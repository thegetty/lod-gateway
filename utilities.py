def PrintToFile(fName, text):
    fh = open(fName, 'w')
    fh.write(text)
    fh.close()
