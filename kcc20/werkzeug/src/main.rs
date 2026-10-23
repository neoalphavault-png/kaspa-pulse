//! Kaspa Pulse, UTXO-Bestand zu einer Stichzeit.
//!
//! Liest die Datenbank eines GESTOPPTEN, synchronen Knotens (Mainnet) und
//! rechnet den UTXO-Bestand auf Stichzeiten zurueck. Kein Netz, keine
//! Knotenadresse, schreibt nichts in die Knoten-Datenbank.
//!
//! Weg 1 (rueckwaerts): virtueller Bestand, minus Diff des Virtual, dann je
//! Kettenblock oberhalb der Stichzeit dessen UTXO-Diff umgekehrt.
//! Weg 2 (vorwaerts, Zweitpruefung): Bestand am Pruning-Punkt, plus die Diffs
//! der Kettenblocke bis zum Stichblock. Beide Wege muessen exakt denselben
//! Bestand liefern, sonst Abbruch (fail closed).
//!
//! Gehalten werden nur Eintraege mit Covenant-ID oder mit P2SH-Skript; fuer den
//! ganzen Bestand werden Anzahl und Summe mitgefuehrt.
//!
//! Aufruf: kp-stichzeit <consensus-db-verzeichnis> <ausgabe-verzeichnis> <stichzeit-ms> [<weitere-ms> ...]
//! Die erste Stichzeit ist die Hauptstichzeit (CSV), die weiteren nur Zaehlungen.

use std::{
    collections::HashMap,
    fs,
    io::{BufWriter, Write},
    path::PathBuf,
    process::exit,
    sync::Arc,
};

use kaspa_addresses::Prefix;
use kaspa_consensus::{
    consensus::storage::ConsensusStorage,
    model::stores::{
        acceptance_data::AcceptanceDataStoreReader, block_transactions::BlockTransactionsStoreReader,
        headers::HeaderStoreReader, pruning::PruningStoreReader, selected_chain::SelectedChainStoreReader,
        utxo_diffs::UtxoDiffsStoreReader, utxo_set::UtxoSetStoreReader, virtual_state::VirtualStateStoreReader,
    },
};
use kaspa_consensus_core::{
    config::{Config, params::MAINNET_PARAMS},
    tx::{ScriptPublicKey, TransactionOutpoint, UtxoEntry},
    utxo::utxo_diff::UtxoDiff,
};
use kaspa_hashes::Hash;
use kaspa_txscript::standard::extract_script_pub_key_address;
use serde_json::json;

type Bestand = HashMap<TransactionOutpoint, UtxoEntry>;

/// P2SH: OP_BLAKE2B OP_DATA_32 <32 bytes> OP_EQUAL, Skriptversion 0.
fn ist_p2sh(spk: &ScriptPublicKey) -> bool {
    let s = spk.script();
    spk.version() == 0 && s.len() == 35 && s[0] == 0xaa && s[1] == 0x20 && s[34] == 0x87
}

fn relevant(e: &UtxoEntry) -> bool {
    // KP_ALLE=1 haelt jeden eintrag, nur fuer den test an einer simulierten kette
    e.covenant_id.is_some() || ist_p2sh(&e.script_public_key) || std::env::var_os("KP_ALLE").is_some()
}

#[derive(Default, Clone, Copy)]
struct Summe {
    anzahl: i128,
    sompi: i128,
}

struct Stand {
    bestand: Bestand,
    alle: Summe,
    fehler: Vec<String>,
}

impl Stand {
    fn neu() -> Self {
        Self { bestand: Bestand::new(), alle: Summe::default(), fehler: vec![] }
    }

    fn rein(&mut self, op: &TransactionOutpoint, e: &UtxoEntry, wo: &str) {
        self.alle.anzahl += 1;
        self.alle.sompi += e.amount as i128;
        if relevant(e) && self.bestand.insert(*op, e.clone()).is_some() {
            self.fehler.push(format!("{wo}: {op} doppelt eingefuegt"));
        }
    }

    fn raus(&mut self, op: &TransactionOutpoint, e: &UtxoEntry, wo: &str) {
        self.alle.anzahl -= 1;
        self.alle.sompi -= e.amount as i128;
        if relevant(e) {
            match self.bestand.remove(op) {
                Some(alt) if alt == *e => {}
                Some(_) => self.fehler.push(format!("{wo}: {op} mit anderem eintrag entfernt")),
                None => self.fehler.push(format!("{wo}: {op} fehlte beim entfernen")),
            }
        }
    }

    /// Diff vorwaerts anwenden (Zustand des Elternblocks -> Zustand des Blocks).
    fn vor(&mut self, d: &UtxoDiff, wo: &str) {
        for (op, e) in d.remove.iter() {
            self.raus(op, e, wo);
        }
        for (op, e) in d.add.iter() {
            self.rein(op, e, wo);
        }
    }

    /// Diff rueckwaerts anwenden (Zustand des Blocks -> Zustand des Elternblocks).
    fn zurueck(&mut self, d: &UtxoDiff, wo: &str) {
        for (op, e) in d.add.iter() {
            self.raus(op, e, wo);
        }
        for (op, e) in d.remove.iter() {
            self.rein(op, e, wo);
        }
    }

    fn kurz(&self) -> serde_json::Value {
        let mut cov = Summe::default();
        let mut p2sh = Summe::default();
        let mut p2sh_ohne = Summe::default();
        for e in self.bestand.values() {
            if e.covenant_id.is_some() {
                cov.anzahl += 1;
                cov.sompi += e.amount as i128;
            }
            if ist_p2sh(&e.script_public_key) {
                p2sh.anzahl += 1;
                p2sh.sompi += e.amount as i128;
                if e.covenant_id.is_none() {
                    p2sh_ohne.anzahl += 1;
                    p2sh_ohne.sompi += e.amount as i128;
                }
            }
        }
        let s = |x: Summe| json!({"utxos": x.anzahl as i64, "sompi": x.sompi.to_string()});
        json!({
            "alle_utxos": s(self.alle),
            "mit_covenant_id": s(cov),
            "p2sh": s(p2sh),
            "p2sh_ohne_covenant_id": s(p2sh_ohne),
        })
    }
}

fn stopp(msg: String) -> ! {
    eprintln!("abbruch: {msg}");
    exit(2)
}

fn iso(ms: u64) -> String {
    // UTC ohne Zusatzcrate: Tage seit 1970 -> Datum (Algorithmus nach Howard Hinnant).
    let s = ms / 1000;
    let (tage, rest) = ((s / 86400) as i64, s % 86400);
    let z = tage + 719468;
    let era = z.div_euclid(146097);
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = yoe + era * 400 + if m <= 2 { 1 } else { 0 };
    format!("{y:04}-{m:02}-{d:02}T{:02}:{:02}:{:02}.{:03}Z", rest / 3600, rest % 3600 / 60, rest % 60, ms % 1000)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 4 {
        stopp("aufruf: kp-stichzeit <consensus-db> <ausgabe> <stichzeit-ms> [<weitere-ms> ...]".into());
    }
    let db_pfad = PathBuf::from(&args[1]);
    let aus = PathBuf::from(&args[2]);
    let mut zeiten: Vec<u64> = args[3..].iter().map(|a| a.parse().unwrap_or_else(|_| stopp(format!("keine ms-zahl: {a}")))).collect();
    let haupt = zeiten[0];
    zeiten.sort_unstable_by(|a, b| b.cmp(a)); // absteigend, so wie zurueckgerechnet wird
    fs::create_dir_all(&aus).unwrap();

    let db = kaspa_database::prelude::ConnBuilder::default()
        .with_db_path(db_pfad)
        .with_create_if_missing(false)
        .with_files_limit(512)
        .build()
        .unwrap_or_else(|e| stopp(format!("datenbank nicht offen: {e}")));
    let config = Arc::new(Config::new(MAINNET_PARAMS));
    let st = ConsensusStorage::new(db, config);

    let virt = st.virtual_stores.read().state.get().unwrap_or_else(|e| stopp(format!("kein virtual state: {e}")));
    let (tip_index, tip) = st.selected_chain_store.read().get_tip().unwrap();
    if tip != virt.ghostdag_data.selected_parent {
        stopp("kettenspitze ist nicht der selected parent des virtual".into());
    }
    let (pp, pp_index) = st.pruning_point_store.read().pruning_point_and_index().unwrap();
    let pp_utxo_pos = st.pruning_meta_stores.read().utxoset_position().unwrap();
    let pp_stabil = st.pruning_meta_stores.read().pruning_utxoset_stable_flag();
    let ts = |h: Hash| st.headers_store.get_timestamp(h).unwrap();
    let daa = |h: Hash| st.headers_store.get_daa_score(h).unwrap();
    let pp_kette = st.selected_chain_store.read().get_by_hash(pp).unwrap_or_else(|e| stopp(format!("pruning-punkt nicht in der kette: {e}")));
    eprintln!(
        "virtual daa {} | kettenspitze {} | pruning-punkt {} index {} ({}) | utxo-position gleich pp: {} | stabil: {}",
        virt.daa_score,
        iso(ts(tip)),
        pp,
        pp_index,
        iso(ts(pp)),
        pp_utxo_pos == pp,
        pp_stabil
    );
    // pp_index zaehlt die pruning-punkte, nicht die kette; fuer die kette gilt pp_kette
    let _ = pp_index;
    let pp_index = pp_kette;
    if ts(pp) >= *zeiten.last().unwrap() {
        stopp(format!("stichzeit {} liegt nicht ueber dem pruning-punkt ({}), kein exakter rueckweg", iso(*zeiten.last().unwrap()), iso(ts(pp))));
    }

    // ---- Weg 1: rueckwaerts ---------------------------------------------------
    let mut w1 = Stand::neu();
    {
        let vs = st.virtual_stores.read();
        for r in vs.utxo_set.seek_iterator(None, usize::MAX, false) {
            let (op, e) = r.unwrap_or_else(|e| stopp(format!("virtual utxo lesen: {e}")));
            w1.rein(&op, &e, "virtual");
        }
    }
    eprintln!("virtual bestand gelesen: {} utxos, davon gehalten {}", w1.alle.anzahl, w1.bestand.len());
    let virtual_kurz = w1.kurz();
    w1.zurueck(&virt.utxo_diff, "virtual-diff");

    let mut idx = tip_index;
    let mut je_zeit = vec![];
    let mut haupt_block = None;
    let mut haupt_bestand = None;
    let mut haupt_alle = Summe::default();
    for &t in &zeiten {
        while ts(st.selected_chain_store.read().get_by_index(idx).unwrap()) > t {
            if idx <= pp_index {
                stopp("rueckweg erreicht den pruning-punkt".into());
            }
            let h = st.selected_chain_store.read().get_by_index(idx).unwrap();
            let d = st.utxo_diffs_store.get(h).unwrap_or_else(|e| stopp(format!("kein utxo-diff fuer kettenblock {h}: {e}")));
            w1.zurueck(&d, "rueckweg");
            idx -= 1;
        }
        let h = st.selected_chain_store.read().get_by_index(idx).unwrap();
        je_zeit.push(json!({
            "stichzeit": iso(t),
            "stichblock": h.to_string(),
            "stichblock_zeit": iso(ts(h)),
            "stichblock_daa": daa(h),
            "kettenindex": idx,
            "bestand": w1.kurz(),
        }));
        if t == haupt {
            haupt_block = Some((idx, h));
            haupt_bestand = Some(w1.bestand.clone());
            haupt_alle = w1.alle;
        }
    }
    let (haupt_idx, haupt_hash) = haupt_block.unwrap();
    let haupt_bestand = haupt_bestand.unwrap();
    if !w1.fehler.is_empty() {
        stopp(format!("rueckweg mit {} fehlern, erster: {}", w1.fehler.len(), w1.fehler[0]));
    }

    // ---- Weg 2: vorwaerts vom pruning-punkt (zweitpruefung) ---------------------
    let mut w2 = Stand::neu();
    let pruefung = if pp_utxo_pos == pp && pp_stabil {
        {
            let pm = st.pruning_meta_stores.read();
            for r in pm.utxo_set.seek_iterator(None, usize::MAX, false) {
                let (op, e) = r.unwrap_or_else(|e| stopp(format!("pruning utxo lesen: {e}")));
                w2.rein(&op, &e, "pruning");
            }
        }
        for i in (pp_index + 1)..=haupt_idx {
            let h = st.selected_chain_store.read().get_by_index(i).unwrap();
            let d = st.utxo_diffs_store.get(h).unwrap_or_else(|e| stopp(format!("kein utxo-diff fuer kettenblock {h}: {e}")));
            w2.vor(&d, "vorweg");
        }
        let gleich = w2.fehler.is_empty()
            && w2.bestand == haupt_bestand
            && w2.alle.anzahl == haupt_alle.anzahl
            && w2.alle.sompi == haupt_alle.sompi;
        json!({
            "weg": "pruning-punkt plus diffs vorwaerts",
            "bestand": w2.kurz(),
            "fehler": w2.fehler.len(),
            "identisch_mit_rueckweg": gleich,
        })
    } else {
        json!({"weg": "nicht moeglich", "grund": "pruning-utxo-bestand nicht stabil oder nicht am pruning-punkt"})
    };
    if pruefung.get("identisch_mit_rueckweg") == Some(&json!(false)) {
        stopp(format!("zweitpruefung weicht ab: {} fehler", w2.fehler.len()));
    }

    // ---- Ausgabe ----------------------------------------------------------------
    let mut ops: Vec<_> = haupt_bestand.iter().collect();
    ops.sort_by_key(|(op, _)| (op.transaction_id, op.index));
    let mut f = BufWriter::new(fs::File::create(aus.join("bestand.csv")).unwrap());
    writeln!(f, "outpoint,sompi,block_daa_score,is_coinbase,covenant_id,klasse,adresse,spk_version,spk_hex").unwrap();
    for (op, e) in ops {
        let adr = extract_script_pub_key_address(&e.script_public_key, Prefix::Mainnet).map(|a| a.to_string()).unwrap_or_default();
        writeln!(
            f,
            "{}:{},{},{},{},{},{},{},{},{}",
            op.transaction_id,
            op.index,
            e.amount,
            e.block_daa_score,
            e.is_coinbase,
            e.covenant_id.map(|c| c.to_string()).unwrap_or_default(),
            if ist_p2sh(&e.script_public_key) { "p2sh" } else { "andere" },
            adr,
            e.script_public_key.version(),
            faster_hex::hex_string(e.script_public_key.script()),
        )
        .unwrap();
    }
    f.flush().unwrap();

    let meta = json!({
        "netz": "mainnet",
        "werkzeug": "kp-stichzeit 0.1.0, rusty-kaspa v2.1.0",
        "hauptstichzeit": iso(haupt),
        "hauptstichblock": haupt_hash.to_string(),
        "virtual_daa": virt.daa_score,
        "kettenspitze_zeit": iso(ts(tip)),
        "pruning_punkt": pp.to_string(),
        "pruning_punkt_zeit": iso(ts(pp)),
        "virtual_bestand": virtual_kurz,
        "stichzeiten": je_zeit,
        "zweitpruefung": pruefung,
    });
    fs::write(aus.join("stand.json"), serde_json::to_string_pretty(&meta).unwrap()).unwrap();

    // ---- Covenant-Transaktionen der vorgehaltenen Kette (KCC-20, 23.10.2026) ----
    // Mit KP_TX=1: jede von der Kette angenommene Transaktion ab dem Pruning-Punkt
    // bis zur Kettenspitze, die einen an eine Covenant-ID gebundenen Ausgang hat
    // oder in einem Eingang das KCC-20-Dispatch-Tag von transfer oder
    // transfer_delegator traegt. Je Tx eine JSON-Zeile mit Eingaengen (Outpoint,
    // Signaturskript) und Ausgaengen (Wert, Skript, Covenant-ID), dazu Zeit und
    // DAA des annehmenden Kettenblocks.
    if std::env::var_os("KP_TX").is_some() {
        const TAGS: [[u8; 5]; 2] = [[0x04, 0x79, 0xc7, 0x1c, 0x23], [0x04, 0xfd, 0x3e, 0xf1, 0x4a]];
        let traegt_tag = |s: &[u8]| s.windows(5).any(|w| TAGS.iter().any(|t| w == t));
        let mut f = BufWriter::new(fs::File::create(aus.join("tx.jsonl")).unwrap());
        let (mut ketten, mut gesehen, mut geschrieben, mut fehlend) = (0u64, 0u64, 0u64, 0u64);
        let mut erste_zeit = None;
        for i in (pp_index + 1)..=tip_index {
            let h = st.selected_chain_store.read().get_by_index(i).unwrap();
            let ad = match st.acceptance_data_store.get(h) {
                Ok(a) => a,
                Err(_) => {
                    fehlend += 1;
                    continue;
                }
            };
            ketten += 1;
            let t = ts(h);
            erste_zeit.get_or_insert(t);
            for mb in ad.iter() {
                let txs = match st.block_transactions_store.get(mb.block_hash) {
                    Ok(x) => x,
                    Err(_) => {
                        fehlend += 1;
                        continue;
                    }
                };
                for e in mb.accepted_transactions.iter() {
                    gesehen += 1;
                    let tx = &txs[e.index_within_block as usize];
                    let rel = tx.outputs.iter().any(|o| o.covenant.is_some()) || tx.inputs.iter().any(|x| traegt_tag(&x.signature_script));
                    if !rel {
                        continue;
                    }
                    let ein: Vec<_> = tx
                        .inputs
                        .iter()
                        .map(|x| {
                            json!([format!("{}:{}", x.previous_outpoint.transaction_id, x.previous_outpoint.index), faster_hex::hex_string(&x.signature_script)])
                        })
                        .collect();
                    let aus_: Vec<_> = tx
                        .outputs
                        .iter()
                        .map(|o| {
                            json!([
                                o.value,
                                o.script_public_key.version(),
                                faster_hex::hex_string(o.script_public_key.script()),
                                o.covenant.map(|c| c.covenant_id.to_string()),
                                o.covenant.map(|c| c.authorizing_input)
                            ])
                        })
                        .collect();
                    writeln!(
                        f,
                        "{}",
                        json!({"id": e.transaction_id.to_string(), "t": t, "daa": daa(h), "ver": tx.version, "in": ein, "out": aus_, "payload": faster_hex::hex_string(&tx.payload)})
                    )
                    .unwrap();
                    geschrieben += 1;
                }
            }
        }
        f.flush().unwrap();
        let tx_meta = json!({
            "kettenbloecke": ketten, "kettenbloecke_ohne_daten": fehlend, "angenommene_tx": gesehen, "covenant_tx": geschrieben,
            "von": erste_zeit.map(iso), "bis": iso(ts(tip)),
        });
        fs::write(aus.join("tx-stand.json"), serde_json::to_string_pretty(&tx_meta).unwrap()).unwrap();
        eprintln!("covenant-tx {} von {} angenommenen tx, kettenbloecke {}, ohne daten {}", geschrieben, gesehen, ketten, fehlend);
    }
    println!("{}", serde_json::to_string_pretty(&meta).unwrap());
}
