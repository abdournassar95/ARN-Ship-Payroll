#!/usr/bin/env bash
# scripts/headless_env.sh
# ------------------------------------------------------------------
# يُهيّئ بيئة تشغيل واختبار «صامتة» (headless) لنظام ARN Ship Payroll
# على أنظمة Linux بلا مكتبات رسوميات — مثل حاويات CI أو بيئات الوكلاء.
#
#   الاستخدام:  bash scripts/headless_env.sh [--skip-tests]
#
# ما يفعله:
#   1) ينشئ .venv ويثبّت requirements.txt
#   2) يبني «stubs» مُصدَّرة بإصدارات (versioned) للمكتبات غير الموجودة في النظام
#      (libGL / libEGL / libxkbcommon / libdbus) لأن Qt6 يطلبها حتى في الوضع offscreen.
#      ⚠ لا تُنشئ stubs لـ libfreetype/libfontconfig: موجودتان فعلاً في النظام،
#        ووضعهما يحجب الخطوط الحقيقية عن Qt.
#   3) يشغّل مجموعة الاختبارات ويتحقّق من النتيجة (إلا مع --skip-tests)
#
# ملاحظة: مجلد .venv ومجلد /tmp/stublibs غير محفوظين في لقطات بيئة الوكلاء،
#         لذا أعد تشغيل هذا السكربت بعد أي إعادة تهيئة للبيئة.
# ------------------------------------------------------------------
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STUBS=/tmp/stublibs
SKIP_TESTS=${1:-}

cd "$REPO"

echo "▶ 1/3 إنشاء البيئة الافتراضية وتثبيت الاعتماديات…"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt

echo "▶ 2/3 بناء stubs المكتبات الناقصة (مُصدَّرة بإصدارات)…"
mkdir -p "$STUBS"
.venv/bin/python - "$STUBS" <<'PY'
import collections, glob, os, re, subprocess, sys

stubs = sys.argv[1]
LIBS = {
    'libGL.so.1':        lambda s: s.startswith('glX') or (s.startswith('gl') and len(s) > 2 and s[2].isupper()),
    'libEGL.so.1':       lambda s: s.startswith('egl'),
    'libxkbcommon.so.0': lambda s: s.startswith('xkb_'),
    'libdbus-1.so.3':    lambda s: s.startswith('dbus_'),
}

refs = collections.defaultdict(lambda: collections.defaultdict(set))
for f in glob.glob('.venv/**/*.so*', recursive=True):
    out = subprocess.run(['readelf', '-W', '--dyn-syms', f],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        toks = line.split()
        if len(toks) < 8 or toks[6] != 'UND':
            continue
        name, _, ver = toks[7].partition('@')
        for lib, match in LIBS.items():
            if name and match(name):
                refs[lib][ver or None].add(name)

for lib, versions in sorted(refs.items()):
    syms = sorted({s for group in versions.values() for s in group})
    base = re.sub(r'[^a-zA-Z0-9_]', '_', lib)
    with open(f'/tmp/{base}.c', 'w') as fh:
        fh.write('\n'.join(f'void {s}(void) {{}}' for s in syms) + '\n')
    with open(f'/tmp/{base}.map', 'w') as fh:
        for ver, group in sorted(versions.items(), key=lambda kv: (kv[0] is not None, kv[0] or '')):
            body = ';\n    '.join(sorted(group))
            fh.write((f'{ver} {{\n  global:\n    {body};\n}};\n') if ver
                     else (f'{{\n  global:\n    {body};\n}};\n'))
    subprocess.run(['gcc', '-shared', '-fPIC', '-w', f'-Wl,-soname,{lib}',
                    f'-Wl,--version-script,/tmp/{base}.map',
                    '-o', f'{stubs}/{lib}', f'/tmp/{base}.c'], check=True)
    print(f'   ✓ {lib} ({len(syms)} رمز)')
PY

if [ "$SKIP_TESTS" != "--skip-tests" ]; then
  echo "▶ 3/3 تشغيل الاختبارات…"
  LD_LIBRARY_PATH="$STUBS" QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q 2>&1 | tail -3
else
  echo "▶ 3/3 تم تخطي الاختبارات (--skip-tests)"
fi

echo
echo "✅ البيئة جاهزة. أمر التشغيل:"
echo "   cd $REPO && LD_LIBRARY_PATH=$STUBS QT_QPA_PLATFORM=offscreen .venv/bin/python -m pytest -q"
