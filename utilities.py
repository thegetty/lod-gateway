import os

# Printing
def PrintToFile(fName, text):
    curr_dir = os.path.dirname(__file__)
    data_dir = os.path.abspath(os.path.join(curr_dir, '..', 'Data'))
    fn = os.path.abspath(os.path.join(data_dir, fName))
    fh = open(fn, 'w')
    fh.write(text)
    fh.close()


# String manipulation
def FindBetween(s, first, last):    
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""
