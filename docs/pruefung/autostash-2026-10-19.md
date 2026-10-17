# `--autostash` in den uebrigen Workflows

Ben, 16.10.2026. Nachtrag zu tagesgrafik #76: dort brach
`git pull --rebase` mit *cannot pull with rebase: You have unstaged
changes* ab (Exit 128), weil ein Skript eine zweite Datei geschrieben
hatte, die nicht im `git add` stand. Der Instagram-Post war live, die
Manifest-Zeile und der Log-Eintrag waren weg.

Betroffen war nur tagesgrafik, weil nur dort eine Datei ausserhalb des
`git add` entsteht. Die uebrigen Workflows sind nicht sicherer, nur noch
nicht betroffen: sobald ein Skript dort eine zweite Datei schreibt,
faellt dieselbe Falle zu. `--autostash` legt alles Ungesicherte vor dem
Rebase beiseite und holt es danach zurueck, statt abzubrechen.

**16 Stellen in 14 Dateien.** Je Zeile ein Tausch, sonst nichts. Ben
aendert sie von Hand, weil es Workflow-Dateien sind.

| Datei | Zeile |
| --- | --- |
| `brevo-send.yml` | 128 |
| `cheat-sheet.yml` | 116 |
| `dashboard-weekly.yml` | 98 |
| `entity-x-heartbeat.yml` | 45 |
| `entityxcostbasis.yml` | 62 |
| `entityxoutflows.yml` | 37 |
| `instagram-antwort.yml` | 60 |
| `instagram-pflege.yml` | 77 |
| `kas-candles.yml` | 55 |
| `reward-cut-alert.yml` | 45 |
| `seiten-zahlen.yml` | 51 |
| `weekly-cancel.yml` | 48 |
| `weekly-guard.yml` | 80 |
| `weekly-guard.yml` | 134 |
| `weekly-guard.yml` | 209 |
| `weeklynumbers.yml` | 99 |

---


## `brevo-send.yml`, Zeile 128

**alt**

```yaml
            git pull --rebase origin main && git push origin HEAD:main && exit 0
```

**neu**

```yaml
            git pull --rebase --autostash origin main && git push origin HEAD:main && exit 0
```

## `cheat-sheet.yml`, Zeile 116

**alt**

```yaml
            git pull --rebase origin "$GITHUB_REF_NAME"
```

**neu**

```yaml
            git pull --rebase --autostash origin "$GITHUB_REF_NAME"
```

## `dashboard-weekly.yml`, Zeile 98

**alt**

```yaml
            git pull --rebase origin main
```

**neu**

```yaml
            git pull --rebase --autostash origin main
```

## `entity-x-heartbeat.yml`, Zeile 45

**alt**

```yaml
            git pull --rebase origin main
```

**neu**

```yaml
            git pull --rebase --autostash origin main
```

## `entityxcostbasis.yml`, Zeile 62

**alt**

```yaml
            git pull --rebase origin main
```

**neu**

```yaml
            git pull --rebase --autostash origin main
```

## `entityxoutflows.yml`, Zeile 37

**alt**

```yaml
            git pull --rebase origin main
```

**neu**

```yaml
            git pull --rebase --autostash origin main
```

## `instagram-antwort.yml`, Zeile 60

**alt**

```yaml
            git pull --rebase origin "$GITHUB_REF_NAME"
```

**neu**

```yaml
            git pull --rebase --autostash origin "$GITHUB_REF_NAME"
```

## `instagram-pflege.yml`, Zeile 77

**alt**

```yaml
            git pull --rebase origin "$GITHUB_REF_NAME"
```

**neu**

```yaml
            git pull --rebase --autostash origin "$GITHUB_REF_NAME"
```

## `kas-candles.yml`, Zeile 55

**alt**

```yaml
            git pull --rebase origin "$GITHUB_REF_NAME"
```

**neu**

```yaml
            git pull --rebase --autostash origin "$GITHUB_REF_NAME"
```

## `reward-cut-alert.yml`, Zeile 45

**alt**

```yaml
            git pull --rebase origin main
```

**neu**

```yaml
            git pull --rebase --autostash origin main
```

## `seiten-zahlen.yml`, Zeile 51

**alt**

```yaml
            git pull --rebase origin "$GITHUB_REF_NAME"
```

**neu**

```yaml
            git pull --rebase --autostash origin "$GITHUB_REF_NAME"
```

## `weekly-cancel.yml`, Zeile 48

**alt**

```yaml
              git pull --rebase origin main && git push origin HEAD:main && break
```

**neu**

```yaml
              git pull --rebase --autostash origin main && git push origin HEAD:main && break
```

## `weekly-guard.yml`, Zeile 80

**alt**

```yaml
            git pull --rebase origin main && git push origin HEAD:main
```

**neu**

```yaml
            git pull --rebase --autostash origin main && git push origin HEAD:main
```

## `weekly-guard.yml`, Zeile 134

**alt**

```yaml
              git pull --rebase origin main && git push origin HEAD:main && break
```

**neu**

```yaml
              git pull --rebase --autostash origin main && git push origin HEAD:main && break
```

## `weekly-guard.yml`, Zeile 209

**alt**

```yaml
              git pull --rebase origin main && git push origin HEAD:main && break
```

**neu**

```yaml
              git pull --rebase --autostash origin main && git push origin HEAD:main && break
```

## `weeklynumbers.yml`, Zeile 99

**alt**

```yaml
          git pull --rebase origin main
```

**neu**

```yaml
          git pull --rebase --autostash origin main
```

---

## Zwei Stellen, die hier absichtlich nicht stehen

`weekly-afternoon.yml` Zeile 182 ist ein `git pull --rebase=false`, also
ein Merge nach einem Branch-Merge. `--autostash` wuerde dort auch wirken,
aber die Stelle steht in einer anderen Lage (sie bringt einen fremden
Branch nach main) und gehoert einzeln angesehen, nicht im Durchlauf
mitgeaendert.

`uhrwerk.yml` hat `--autostash` seit dem ersten Entwurf.
