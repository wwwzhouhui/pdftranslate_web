from pdf2docx import Converter

#pdf_file = 'D:\\工作临时\\2025\\10月\\2025年10月11日\\translated_dual.pdf'
#docx_file = 'D:\\工作临时\\2025\\10月\\2025年10月11日\\translated_dual.docx'

pdf_file = '/mnt/f/work/code/github/wwwzhouhui/pdftranslate_web/output/ReStoCNet.pdf'
docx_file = '/mnt/f/work/code/github/wwwzhouhui/pdftranslate_web/output/ReStoCNet.docx'

# convert pdf to docx
cv = Converter(pdf_file)
cv.convert(docx_file)      # all pages by default
cv.close()