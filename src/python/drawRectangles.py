from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.layout import LTTextBoxHorizontal, LTChar, LTWord, LTNumber
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import portrait, letter, A4
from PyPDF2 import PdfFileWriter, PdfFileReader
import os
import sys
import subprocess

def merger(filePath, temporaryPDF, outputFile):
    overlay = PdfFileReader(open(temporaryPDF, 'rb'))
    background = PdfFileReader(open(filePath, 'rb')).getPage(0)
    output = PdfFileWriter()

    page = overlay.getPage(0)
    page.mergePage(background)
    output.addPage(page)

    with open(outputFile, 'wb') as f:
       output.write(f)


def drawRectangles(filePath, temporaryPDF):
    '''draws rectanlges around each LTWord / LTNumber object on page 0
    of the pdf "filePath".'''
    #Create resource manager
    rsrcmgr = PDFResourceManager()
    # Set parameters for analysis.
    laparams = LAParams()
    # Create a PDF page aggregator object.
    device = PDFPageAggregator(rsrcmgr, laparams = laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)

    with open(filePath, 'rb') as document:
        page = list(PDFPage.get_pages(document, pagenos = 2))[0]
        vejPageSize = tuple(page.mediabox[2:4])
        cv = canvas.Canvas(temporaryPDF, pagesize = vejPageSize)
        interpreter.process_page(page)
        layout = device.get_result()
        for elem in layout:
            for e in elem:
                for item in e:
                    if isinstance(item, LTWord):
                        cv.rect(item.x0, item.y0, item.width, item.height)
        cv.save()



def main(fileName, inputPath, outputPath):
    temporaryPDF = os.path.join(outputPath, 'temp.pdf')
    filePath = os.path.join(inputPath, fileName)
    pdfCustomEncoder(filePath, temporaryPDF)
    outputFile = os.path.join(outputPath, fileName[:-4] + '_overlayed.pdf')
    merger(filePath, temporaryPDF, outputFile)
    # remove temp.pdf
    os.remove(temporaryPDF)
    subprocess.run(['open', outputFile], check = True)



if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('usage: \n\tfileName inputPath [outputPath (default inputPath)]\n\tadditional arguments will be ignored')
        sys.exit(0)
    else:
        fileName = sys.argv[1]
        inputPath = sys.argv[2]
        try:
            outputPath = sys.argv[3]
        except IndexError:
            outputPath = inputPath
    main(fileName, inputPath, outputPath)
