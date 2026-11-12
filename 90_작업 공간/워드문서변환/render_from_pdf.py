"""Run the packaged DOCX rasterizer using a native Word PDF export on Windows."""
from pathlib import Path
import sys, importlib.util, argparse, os
import pdf2image

SKILL=Path('C:/Users/cellbig/.codex/plugins/cache/openai-primary-runtime/documents/26.1104.12130/skills/documents')
POPPLER='C:/Users/cellbig/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin'
if '--output_dir' in sys.argv:
    ap=argparse.ArgumentParser()
    ap.add_argument('docx',type=Path)
    ap.add_argument('--output_dir',type=Path,required=True)
    args=ap.parse_args()
    docx=str(args.docx.resolve());out=str(args.output_dir.resolve())
    name='reference.pdf' if args.docx.name.startswith('무형문화유산') else 'cave_action.pdf'
    pdf=str(Path(__file__).resolve().parent/'검증'/name)
    if not args.docx.name.startswith('무형문화유산') and os.environ.get('WORD_QA_PDF'):
        pdf=str(Path(os.environ['WORD_QA_PDF']).resolve())
else:
    docx, pdf, out = map(lambda x:str(Path(x).resolve()),sys.argv[1:4])
spec=importlib.util.spec_from_file_location('packaged_docx_renderer',SKILL/'render_docx.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.convert_to_pdf=lambda *a,**k:(pdf,'Native Microsoft Word PDF export; retained DOCX unchanged')
mod.pdfinfo_from_path=lambda *a,**k:pdf2image.pdfinfo_from_path(*a,poppler_path=POPPLER,**k)
mod.convert_from_path=lambda *a,**k:pdf2image.convert_from_path(*a,poppler_path=POPPLER,**k)
sys.argv=[str(SKILL/'render_docx.py'),docx,'--output_dir',out,'--emit_pdf','--dpi','120']
mod.main()
