#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""testwallet_neu.py, laeuft auf Bens Rechner, nie auf dem Runner.

Erzeugt einen frischen Kaspa-Schluessel fuer die Test-Wallet A des Experiments
"100 Zahlungen" und gibt ihn NUR in eine Pipe aus, direkt in GitHub Secrets.
Auf den Bildschirm kommt nur die Adresse A. Der Schluessel steht so nie im
Terminal, nie in einer Datei, nie im Chat (Regel vom 02.10.2026).

    pip install kaspa==2.1.0
    python3 scripts/testwallet_neu.py | gh secret set KASPA_TESTWALLET_PRIVKEY \\
        --env testwallet --repo neoalphavault-png/kaspa-pulse

Danach die angezeigte Adresse als Variable setzen (kein Secret, sie ist
oeffentlich):

    gh variable set KASPA_TESTWALLET_ABSENDER --env testwallet \\
        --repo neoalphavault-png/kaspa-pulse --body "kaspa:..."

Eine Sicherung des Schluessels gibt es absichtlich nicht. Der Lauf gibt am Ende
den Rest an B zurueck, danach werden Secret und Environment geloescht.
"""
import sys


def main():
    if sys.stdout.isatty():
        sys.stderr.write("ABBRUCH die ausgabe geht auf den bildschirm. nur mit pipe in "
                         "'gh secret set' aufrufen, siehe kopf der datei.\n")
        return 1
    import kaspa
    kp = kaspa.Keypair.random()
    adresse = str(kp.to_address("mainnet"))
    sys.stdout.write(kp.private_key)
    sys.stdout.flush()
    sys.stderr.write("adresse A (oeffentlich): %s\n" % adresse)
    sys.stderr.write("der schluessel ging nur in die pipe.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
