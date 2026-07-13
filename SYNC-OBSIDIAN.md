# GitHub → Obsidian per systemd

```bash
git clone https://github.com/H234598/ADHS-Lernpfad.git
cd ADHS-Lernpfad
./scripts/install-obsidian-sync.sh "/vollstaendiger/Pfad/zum/Obsidian-Vault"
```

Der Benutzertimer synchronisiert alle 30 Minuten per Fast-Forward. Lokale Änderungen werden niemals überschrieben; der Lauf bricht dann kontrolliert ab.

```bash
systemctl --user status adhs-lernpfad-sync.timer
journalctl --user -u adhs-lernpfad-sync.service -n 100 --no-pager
```
