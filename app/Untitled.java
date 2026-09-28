cd ~/bilimai

python - <<'PYEOF'
from pathlib import Path
p = Path("app/templates/base.html")
s = p.read_text()
old = 'family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap'
new = 'family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&family=Caveat:wght@500;700&display=swap'
if old in s:
    s = s.replace(old, new)
    p.write_text(s)
    print("✓ Caveat shrift qo'shildi")
else:
    print("⚠ Allaqachon qo'shilgan bo'lishi mumkin")
PYEOF