from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.layout import LTTextBoxHorizontal, LTWord, LTNumber, LTSpecialCharacter
import json, sys

# table of contents in json-Style:
# {'header' : 'header1',
#  'page'   : 10,
#  'subheaders: [
#       'subheader' : 'subheader1',
#       'page'      : 15
#       ]}

def LTTextBoxHorizontalToListofHeaders(element):
    assert isinstance(element, LTTextBoxHorizontal)

    return  list(filter(None, element.get_text().split('\n')))

def isListOfNumbers(listToCheck):
    '''checks whether a list of string is actually a list of number represented
    as strings'''

    return all((item.isdigit() for item in listToCheck))

def stringListToIntList(stringList):
    '''converts a list of digits as string into a list with integers'''
    return [int(str) for str in stringList]

def jsonizeEntry(header, pageNumber):
    isSubheader = True
    entry = {'header' : header,
             'page'   : pageNumber}
    # if header is not a subheader then add the 'subheaders' key
    # this avoids cluddering of the json file with empty lists
    if not 'Teil' in header:
        isSubheader = False
        entry.update({'subheaders' : []})
    return isSubheader, entry

def getTableOfContentLayout(document, interpreter, device):
    for page in PDFPage.get_pages(document):
        interpreter.process_page(page)

        # receive the LTPage object for the page.
        layout = device.get_result()

        # check if it is the correct page ('Inhalt' must be in first element)
        if layout[0].get_text().rstrip() == 'Inhalt':
            return layout

def mergeSubHeaers(headers):
    '''Merges individual String of the subheader into one string.
    Since the parsing logic uses "\\n" for splitting headers it also subdivide
    the subheader into two individual strings (the layout of the subheader in
    the pdf file being ('Part 1\nSome Subheader')).'''

    # find entry in headers list which contains 'Teil' keyword
    # merge entry with secutive entry
    for i, header in enumerate(headers):
        if 'Teil' in header:
            headers[i] = ' '.join((header, headers[i + 1]))
            headers.pop(i + 1)
    return headers

def parseTableOfContentLayout(layout):
    '''parses the content of the layout object and creates two list.
    headers contains the string for the headers in the pdfDocument and
    pageNumbers contains the associated pageNumbers'''
    headers = []
    pageNumbers = []
    for element in layout[1:]: #skip first element since that must be 'Inhalt'
        if isinstance(element, LTTextBoxHorizontal):
            parsedList = LTTextBoxHorizontalToListofHeaders(element)
            if isListOfNumbers(parsedList):
                pageNumbers += stringListToIntList(parsedList)
            else:
                headers += parsedList

    # sanitize headers (merge subheaders)
    headers = mergeSubHeaers(headers)
    return headers, pageNumbers

def getTableOfContent(document, interpreter, device):
    TOC = []
    layout = getTableOfContentLayout(document, interpreter, device)
    headers, pageNumbers = parseTableOfContentLayout(layout)

    if len(headers) != len(pageNumbers):
        print('Something went wrong!')
        print('headers: {:d}, pageNumbers: {:d}'.format(len(headers), len(pageNumbers)))
        print('headers: ', headers)

    for header, pageNumber in zip(headers, pageNumbers):
        isSubheader, entry = jsonizeEntry(header, pageNumber)
        if isSubheader:
            TOC[-1]['subheaders'].append(entry)
        else:
            TOC.append(entry)

    return TOC

def getDocumentKeys(textline):
    for obj in textline:
        if isinstance(obj, LTNumber):
            break
        if isinstance(obj, LTWord) or isinstance(obj, LTSpecialCharacter):
            yield obj


def getDocumentNumbers(textline):
    for obj in textline:
        if isinstance(obj, LTNumber):
            yield obj


def extractDocumentKeywords(document, pageNumbers, interpreter, device):
    documentIndex = []
    for page in PDFPage.get_pages(document, pagenos = pageNumbers):
        interpreter.process_page(page)
        layout = list(device.get_result())

        isSubkey = False
        isIndented = False
        for textBox in layout[2:]:
            if isinstance(textBox, LTTextBoxHorizontal):
                x0 = textBox.x0
                for textLine in textBox:
                    if textLine.x0 == x0:
                        isIndented = False
                        if isinstance(textLine[0], LTSpecialCharacter):
                            isSubkey = True
                        else:
                            isSubkey = False
                    else:
                        isIndented = True
                    # parse line
                    documentKeys = getDocumentKeys(textLine[(isSubkey * 2):])
                    documentNumbers = getDocumentNumbers(textLine[(isSubkey * 2):])

                    if isIndented & isSubkey: # add to last subkey entry
                        updateKeyEntry(documentIndex[-1]['documentSubkeys'][-1], documentKeys, documentNumbers)
                    elif isIndented & (not isSubkey): # add to last main key entry
                        updateKeyEntry(documentIndex[-1], documentKeys, documentNumbers)
                    else: # make entry
                        entry = jsonizeKeyEntry(documentKeys, documentNumbers)
                        # print(json.dumps(entry, indent = 2))
                        if isSubkey: # append subkeys to the last mainkey entry
                            documentIndex[-1]['documentSubkeys'].append(entry)
                        else:
                            documentIndex.append(entry)

    return documentIndex

def jsonizeKeyEntry(keys, documentNumbers):
    entry = {'documentKey' : ' '.join((key.get_text() for key in keys)),
             'documentNumbers' : [documentNumber.string2number() for documentNumber in documentNumbers],
             'documentSubkeys' : []}

    return entry

def updateKeyEntry(entry, keys, numbers):
    entry['documentKey'] += ' '.join((key.get_text() for key in keys))
    entry['documentNumbers'] += [number.string2number() for number in numbers]


def getPageNumbers(TOC, header, maxPage):
    '''returns all pageNumbers for a header as a list'''
    start = 0
    end = 0
    for i, entry in enumerate(TOC):
        if entry['header'] == header:
            start = entry['page']
            try:
                end = TOC[i + 1]['page']
            except IndexError:
                end = maxPage
            break

    # -1 since pdfminer is 0-based index, and pdf document is 1-based index
    pageNumbers = list(range(start - 1, end - 1))
    return pageNumbers

def main():
    #Create resource manager
    rsrcmgr = PDFResourceManager()
    # Set parameters for analysis.
    laparams = LAParams(line_margin = 0.8, all_texts = True)

    # Create a PDF page aggregator object.
    device = PDFPageAggregator(rsrcmgr, laparams = laparams)
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    with open('../../data/VEJ 6.pdf', 'rb') as document:
        TOC = getTableOfContent(document, interpreter, device)
        pageNumbers = getPageNumbers(TOC, 'Systematischer Dokumentenindex', 878)
        documentIdx = extractDocumentKeywords(document, pageNumbers, interpreter, device)

    with open('Systematischer_Dokumentenindex.json', 'w') as docIdx:
        json.dump(documentIdx, docIdx, indent =  2)



if __name__ == '__main__':
    main()
