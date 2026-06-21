from PyPDF2 import PdfWriter
from pathlib import Path
from extract import trim_pdf

p=Path('sample_test.pdf')
writer=PdfWriter()
for i in range(1,6):
    writer.add_blank_page(width=72, height=72)
with open(p,'wb') as f:
    writer.write(f)
print('created',p)
trimmed=trim_pdf(str(p), start_page=2, end_page=3, output_path='trimmed_sample.pdf')
print('trimmed ->',trimmed, 'exists=', Path(trimmed).exists())
