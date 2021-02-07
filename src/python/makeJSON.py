import pandas as pd
import re
import csv
import json
from geopy.geocoders import Nominatim

def flatten(tupleOfTuples):
    for element in tupleOfTuples:
        if isinstance(element, tuple):
            yield from flatten(element)
        else:
            yield element

def readTxtFile(txtFile):
    output = []
    count = -1
    with open(txtFile, 'r') as fp:
        line = fp.readline()
        while line:
            # do parsing stuff
            if not line.startswith('\u2013 '):
                # if line does not start with '- ' we have a main key
                match = re.search("\d", line)
                keyword = line[:match.start() - 1]
                output.append({'documentMainKey' : keyword,
                              'documentNumbers' : [int(documentNumber) for documentNumber in re.findall(r'\d+', line[match.start():])],
                              'documentSubkeys' : []})
                count += 1
            else:
                match = re.search("\d", line)
                subkey = line[2:match.start() - 1]
                output[count]['documentSubkeys'].append({'documentSubkey' : subkey,
                                          'documentNumbers' : [int(documentNumber) for documentNumber in re.findall(r'\d+', line[match.start():])]})
            line = fp.readline()

    return output

def documentNumbers(inputJSON):
    documents = set()
    for entry in inputJSON:
        for documentNumber in entry['documentNumbers']:
            documents.add(documentNumber)
        if not len(entry['documentSubkeys']) == 0:
            for subentry in entry['documentSubkeys']:
                for documentNumber in subentry['documentNumbers']:
                    documents.add(documentNumber)
    return sorted(documents)

def makeDocumentLookupList(documentNumberList):
    documentLookupList = [0] * (max(documentNumberList) + 1)
    for idx, documentNumber in enumerate(documentNumberList):
        documentLookupList[documentNumber] = idx
    return documentLookupList

def makeCSV(documents):
    with open("data/documents.csv", 'w', newline = '') as myfile:
        wr = csv.writer(myfile, dialect = 'excel', delimiter = '\n')
        wr.writerow(documents)

def pdDataFrameToGeoJSON(pdDataFrame, properties, lon = 'longitude', lat = 'latitude'):
    # create geoJSON skeleton container:
    geoJSON = {'type' : 'FeatureCollection',
               'features' : []
               }
    for _, row in pdDataFrame.iterrows():
        feature = {'type' : 'Feature',
                   'geometry' : {
                        'type' : 'Point',
                        'coordinates' : [row[lon], row[lat]]
                   },
                    'properties' : {}}
        for property in properties:
            feature['properties'][property] = row[property]
        feature['properties']['documentKeys'] = [{'documentMainKey' : '',
                                                  'documentSubkeys' : []}]
        geoJSON['features'].append(feature)

    return geoJSON

def addDocumentKeysToGeoJSON(geoJSON, documentKeyJSON, documentLookupList):
    for i, documentKey in enumerate(documentKeyJSON):
        for documentNumber in documentKey['documentNumbers']:
            try:
                geoJSON['features'][documentLookupList[documentNumber]]['properties']['documentKeys'][i]['documentMainKey'] = documentKey['documentMainKey']
            except IndexError:
                pass
        for documentSubkey in documentKey['documentSubkeys']:
            for documentNumber in documentSubkey['documentNumbers']:
                try:
                    if not geoJSON['features'][documentLookupList[documentNumber]]['properties']['documentKeys'][i]['documentMainKey']:
                        geoJSON['features'][documentLookupList[documentNumber]]['properties']['documentKeys'][i]['documentMainKey'] = documentKey['documentMainKey']
                    geoJSON['features'][documentLookupList[documentNumber]]['properties']['documentKeys'][i]['documentSubkeys'].append(documentSubkey['documentSubkey'])
                except IndexError:
                    pass

    return geoJSON

def addCoordinatesToPdDataframe(pdDataFrame):
    geolocator = Nominatim(user_agent = 'coordinateMaker', timeout = 10)
    lambdaFunction = lambda x : pd.Series(list(flatten(geolocator.geocode(x['documentLocation']))), index = ['documentLocation', 'latitude', 'longitude'])
    coordinates = pdDataFrame.apply(lambdaFunction, axis = 1, result_type = 'expand')
    pdDataFrame = coordinates.combine_first(pdDataFrame)
    # for _, row in pdDataFrame.iterrows():
    #     print(row['documentLocation'])
    #     print(geolocator.geocode(row['documentLocation'])[1])

    return pdDataFrame

if __name__ == '__main__':
    testIdx = readTxtFile('data/testIndex.txt')
    # print(json.dumps(testIdx, indent = 2))
    with open('testIndex.json', 'w') as outJSON:
        json.dump(testIdx, outJSON)
    documents = documentNumbers(testIdx)
    documentLookupList = makeDocumentLookupList(documents)

    # load documents.csv as pandas dataframe
    documentsTable = pd.read_csv('data/documents_with_coordinates.csv')
    # documentsTable = documentsTable.iloc[:,:3]
    # # remove documents that are not yet filled with title and location
    # documentsTable = documentsTable[documentsTable.documentTitle.notnull()]
    # # print(documentsTable[documentsTable.documentTitle.notnull()])
    # documentsTable = addCoordinatesToPdDataframe(documentsTable)

    # documentsTable.to_csv('data/documents_with_coordinates.csv')
    # transform dataframe into geoJSON
    geoJSON = pdDataFrameToGeoJSON(documentsTable, properties = ['documentNumber', 'documentTitle', 'documentLocation'])
    # add document key information to geoJson
    geoJSON = addDocumentKeysToGeoJSON(geoJSON, testIdx, documentLookupList)

    with open('testDocuments.json', 'w') as outGeoJSON:
        json.dump(geoJSON, outGeoJSON, indent = 2)
