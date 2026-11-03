//! Kaspa Pulse, Coinbase-Ausgaben und ihre erste Ausgabe (Ben, 02.11.2026, Miner nach dem Reward Cut).
//!
//! Liest die Datenbank eines GESTOPPTEN, synchronen Mainnet-Knotens. Je
//! Kettenblock ueber `ab_daa` (oder ueber dem Pruning-Punkt) steht im UTXO-Diff,
//! welche Ausgaben dazukamen und welche ausgegeben wurden. Ein ausgegebener
//! Eintrag traegt seinen Betrag, den DAA-Score seiner Entstehung und ob er aus
//! einer Coinbase stammt. Damit braucht es keinen eigenen Bestand: jede
//! Coinbase-Ausgabe wird einmal ausgegeben, und zwar in dem Kettenblock, dessen
//! Diff sie entfernt.
//!
//! Ausgabe, ohne Adresse, ohne Skript, ohne Tx-ID:
//!   rein.csv      je UTC-Minute der Kettenbloecke: neue Coinbase-Ausgaben, Anzahl und sompi
//!   raus.csv      je ausgegebener Coinbase-Ausgabe: DAA-Score der Entstehung, Zeit der Ausgabe (ms), sompi
//!   daa-zeit.csv  je UTC-Minute: kleinster und groesster DAA-Score der Kettenbloecke darin
//!   stand.json    Pruning-Punkt, Kettenspitze, gelesener Bereich, Summen
//!
//! Aufruf: kp-coinbase <consensus-db-verzeichnis> <ausgabe-verzeichnis> <ab_daa, 0 = ab pruning-punkt>

use std::{
    collections::BTreeMap,
    fs,
    io::{BufWriter, Write},
    path::PathBuf,
    process::exit,
    sync::Arc,
};

use kaspa_consensus::{
    consensus::storage::ConsensusStorage,
    model::stores::{
        headers::HeaderStoreReader, pruning::PruningStoreReader, selected_chain::SelectedChainStoreReader,
        utxo_diffs::UtxoDiffsStoreReader, virtual_state::VirtualStateStoreReader,
    },
};
use kaspa_consensus_core::config::{Config, params::MAINNET_PARAMS};
use kaspa_hashes::Hash;
use serde_json::json;

fn stopp(msg: String) -> ! {
    eprintln!("abbruch: {msg}");
    exit(2)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 4 {
        stopp("aufruf: kp-coinbase <consensus-db> <ausgabe> <ab_daa>".into());
    }
    let db_pfad = PathBuf::from(&args[1]);
    let aus = PathBuf::from(&args[2]);
    let ab_daa: u64 = args[3].parse().unwrap_or_else(|_| stopp(format!("keine zahl: {}", args[3])));
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
    let (pp, _) = st.pruning_point_store.read().pruning_point_and_index().unwrap();
    let ts = |h: Hash| st.headers_store.get_timestamp(h).unwrap();
    let daa = |h: Hash| st.headers_store.get_daa_score(h).unwrap();
    let pp_index = st.selected_chain_store.read().get_by_hash(pp).unwrap_or_else(|e| stopp(format!("pruning-punkt nicht in der kette: {e}")));
    if ab_daa > 0 && daa(pp) > ab_daa {
        stopp(format!("luecke: pruning-punkt daa {} liegt ueber ab_daa {}", daa(pp), ab_daa));
    }

    let mut rein: BTreeMap<u64, (u64, u64)> = BTreeMap::new(); // minute -> (anzahl, sompi)
    let mut zeit: BTreeMap<u64, (u64, u64)> = BTreeMap::new(); // minute -> (daa min, daa max)
    let mut raus = BufWriter::new(fs::File::create(aus.join("raus.csv")).unwrap());
    writeln!(raus, "erzeugt_daa,ausgegeben_ms,sompi").unwrap();
    let (mut n_rein, mut n_raus, mut s_rein, mut s_raus, mut bloecke) = (0u64, 0u64, 0u128, 0u128, 0u64);
    let (mut erster, mut letzter): (Option<(u64, u64)>, Option<(u64, u64)>) = (None, None);
    let mut i = pp_index + 1;
    while i <= tip_index {
        let h = st.selected_chain_store.read().get_by_index(i).unwrap();
        i += 1;
        let d_score = daa(h);
        if d_score <= ab_daa {
            continue;
        }
        let t = ts(h);
        let minute = t / 60000 * 60000;
        let d = st.utxo_diffs_store.get(h).unwrap_or_else(|e| stopp(format!("kein utxo-diff fuer kettenblock {h}: {e}")));
        for e in d.add.values().filter(|e| e.is_coinbase) {
            let r = rein.entry(minute).or_insert((0, 0));
            r.0 += 1;
            r.1 += e.amount;
            n_rein += 1;
            s_rein += e.amount as u128;
        }
        for e in d.remove.values().filter(|e| e.is_coinbase) {
            writeln!(raus, "{},{},{}", e.block_daa_score, t, e.amount).unwrap();
            n_raus += 1;
            s_raus += e.amount as u128;
        }
        let z = zeit.entry(minute).or_insert((d_score, d_score));
        z.0 = z.0.min(d_score);
        z.1 = z.1.max(d_score);
        if erster.is_none() {
            erster = Some((d_score, t));
        }
        letzter = Some((d_score, t));
        bloecke += 1;
    }
    raus.flush().unwrap();
    let mut f = BufWriter::new(fs::File::create(aus.join("rein.csv")).unwrap());
    writeln!(f, "minute_ms,anzahl,sompi").unwrap();
    for (m, (n, s)) in &rein {
        writeln!(f, "{m},{n},{s}").unwrap();
    }
    let mut f = BufWriter::new(fs::File::create(aus.join("daa-zeit.csv")).unwrap());
    writeln!(f, "minute_ms,daa_min,daa_max").unwrap();
    for (m, (a, b)) in &zeit {
        writeln!(f, "{m},{a},{b}").unwrap();
    }
    let stand = json!({
        "pruning_punkt_daa": daa(pp),
        "pruning_punkt_ms": ts(pp),
        "kettenspitze_daa": daa(tip),
        "kettenspitze_ms": ts(tip),
        "ab_daa": ab_daa,
        "erster_daa": erster.map(|x| x.0),
        "erster_ms": erster.map(|x| x.1),
        "letzter_daa": letzter.map(|x| x.0),
        "letzter_ms": letzter.map(|x| x.1),
        "kettenbloecke": bloecke,
        "coinbase_neu": n_rein,
        "coinbase_neu_sompi": s_rein.to_string(),
        "coinbase_ausgegeben": n_raus,
        "coinbase_ausgegeben_sompi": s_raus.to_string(),
    });
    fs::write(aus.join("stand.json"), serde_json::to_string_pretty(&stand).unwrap()).unwrap();
    eprintln!("{}", serde_json::to_string(&stand).unwrap());
}
