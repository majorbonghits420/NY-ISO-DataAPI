# Used for grabbing new data from the NYISO website directly
import urllib.request
# Used for better formatting the request url to more easily loop through dates
import time
# For dealing with ZIP files
import zipfile
# For dealing with reading response from url requests
import io
from datetime import date
import datetime
# For creating matrices
import numpy
import calendar

NUM_ZONES = 15
NUM_USED_ZONES = 11
NUM_HOURS = 24
SKIP_ZONES = [4, 11, 12, 13]
DST_SPRING = ['20160313', '20150308', '20170312']
DST_FALL = ['20161106', '20151101']

"""
Brief: Takes in a matrix and a filename, outputs the matrix to the filename as a
CSV file.

Parameter matrix - A 2D list to be put into the file, where indexing is row, col
paramter filename - The file to be written to
"""
def wrMatrixToFile(matrix, filename):
    # Open the file, and specify we are writing to it
    fid = open(filename, "w")
    for row in matrix:
        for col in row:
            # Write the value
            fid.write(str(col) + ",")
        # Add a newline to begin the next row
        fid.write("\n")

"""
Brief: Takes in a date and gets the corresponding real time or day ahead data
  from NYISO and appends it on to the specified file. It only appends on the
  price data. It is assumed that we know the ordering of the locations and
  that time. It then returns a list of the prices. The way that the data is
  appended to the file is that all values are added to a new line, and
  seperated by commas. This only works for the single day files that NYISO
  hosts. If the date corresponds with DST then we double hour 1 when we spring
  forward, and remove the second interation of hour 1 when we fall back

Parameter time - A Date object specifying the date to get data for
Parameter RTorDA - Either "RT" or "DA" is accepted, this specifies if the user
  wants the Real Time or Day Ahead data for the specified date
Paramter filename - The file to which the data will be appended. If there is
  no file with the filename, a new one will be created
"""
def appendDateData(t, RTorDA, filename):
    # Open the file to be appended to
    fid = open(filename, 'a')
    # Generate URL
    url = genDayURL(t, RTorDA)
    # Grab the file from the URL
    response = urllib.request.urlopen(url)
    # Read the data as utf-8 into a string format
    data = response.read()
    data = data.decode('utf-8')
    # Divide the data into different lines
    lines = str.splitlines(data)
    firstLine = True
    # Counter to keep track of what location we are on
    counter = 0
    springFwd = checkDSTFwd(url)
    fallBack = checkDSTBack(url)
    buff = []
    hour = 0
    for line in lines:
        if (firstLine):
          firstLine = False
          continue
        if (counter in SKIP_ZONES):
            counter = (counter + 1) % NUM_ZONES
            continue
        # Skip extra hour on falling back
        if (fallBack and hour == 2):
            continue
        # Split each line into a list of columns which are marked by commas
        columns = line.split(',')
        # Replace the list with the price data that we actually care about
        line = columns[3]
        if (len(buff) < 24):
          buff.append(str(line))
        else:
          buff[0:NUM_HOURS - 1] = buff[1:]
          buff[NUM_HOURS - 1] = str(line)
        fid.write(str(line) + ',')
        counter = (counter + 1) % NUM_ZONES
        hour += 1
        # Repeat last hour on springing forward
        if (springFwd and hour == 2):
          for data in buff:
            fid.write(line + ',')
    fid.write("\n")
    return

def checkDSTFwd(string):
  toReturn = False
  for x in DST_SPRING:
    toReturn |= (x in string)
  return toReturn

def checkDSTBack(string):
  toReturn = False
  for x in DST_FALL:
    toReturn |= (x in string)
  return toReturn

"""
Brief: Takes in a date and gets the corresponding real time or day ahead data
  from NYISO and appends it on to the specified file. It only appends on the
  price data. It is assumed that we know the ordering of the locations and
  that time. It then returns a list of the prices. They way that the data is
  appended to the file is that all values are added to a new line, and
  seperated by commas. This only works for the single day files that NYISO
  hosts. If a date is when DST happens, when we spring forward we duplicate hour
  1 and when falling back we remove the second iteration of hour 1.

Parameter time - A Date object specifying the month and year to get data for
Parameter RTorDA - Either "RT" or "DA" is accepted, this specifies if the user
  wants the Real Time or Day Ahead data for the specified date
Paramter filename - The file to which the data will be appended. If there is
  no file with the filename, a new one will be created
"""
def grabMonthData(t, RTorDA, filename):
  # file to write
  ftw = open(filename, 'a')
  # Generate URL
  url = genMonthURL(t, RTorDA)
  # Send HTTP GET request
  try:
      response = urllib.request.urlopen(url)
  except:
      print("could not reach " + url)
      return
  data = response.read()
  # Extract the zipped file from the HTTP response
  zippedFile = zipfile.ZipFile(io.BytesIO(data))
  # For each file in zipped file, read contents of file into a new file
  for fid in zippedFile.namelist():
    firstLine = True
    counter = 0
    springFwd = checkDSTFwd(fid)
    fallBack = checkDSTBack(fid)
    buff = []
    hour = 0
    for line in zippedFile.open(fid):
      if (firstLine):
        firstLine = False
        continue
      if (counter in SKIP_ZONES):
        counter = (counter + 1) % NUM_ZONES
        continue
      if (fallBack and hour == 2):
        continue
      cols = (line.decode("utf-8")).split(",")
      # Only data we care about
      line = cols[3]
      ftw.write(str(line) + ",")
      counter = (counter + 1) % NUM_ZONES
      if (len(buff) < NUM_HOURS):
        buff.append(str(line))
      else:
        buff[0:NUM_HOURS - 1] = buff[1:]
        buff[NUM_HOURS - 1] = str(line)
      hour += 1
      if (springFwd and hour == 2):
        for data in buff:
          ftw.write(x + ',')
    # Write a newline because it is a new day
    ftw.write("\n")
  return

"""
Brief: Takes in a string and determines if the string is asking for realtime or
  dayahead prices. Returns True for Realtime and False for Day Ahead. Returns an
  error if the input is neither of these.

Parameter string - The string to be checked for it is "RT" or DA"
"""
def realtimeCheck(string):
  if (string == "RT"):
    return True
  elif (string == "DA"):
    return False
  else:
    raise ValueError("Wrong input: must be 'RT' or 'DA'")

"""
Brief: Generate a URL to get Realtime or Day-Ahead pricings based on a month
"""
def genMonthURL(t, RTorDA):
  url = "http://mis.nyiso.com/public/csv/"
  urlEnd = "_zone_csv.zip"
  if (realtimeCheck(RTorDA)):
      url += "rtlbmp/"
      urlEnd = "rtlbmp" + urlEnd
  else:
      url += "damlbmp/"
      urlEnd = "damlbmp" + urlEnd
  urlEnd = "01" + urlEnd
  date = str(t.year) + ('0' + str(t.month), str(t.month))[t.month > 10]
  url = url + date + urlEnd
  return url

"""
Brief: Generate a URL to get Realtime or Day-Ahead pricings based on a given date
"""
def genDayURL(t, RTorDA):
  # Baseline URL
  url = "http://mis.nyiso.com/public/csv/"
  # Base ending of the URL
  urlEnd = "_zone.csv"
  if (realtimeCheck(RTorDA)):
      url += "rtlbmp/"
      urlEnd = "rtlbmp" + urlEnd
  else:
      url += "damlbmp/"
      urlEnd = "damlbmp" + urlEnd
  # Add the specified time to the URL
  dates = str(t.year) + ('0' + str(t.month), str(t.month))[t.month > 10]
  dates += ('0' + str(t.day), str(t.day))[t.day > 10]
  url = url + dates + urlEnd
  return url

"""
Brief: Takes in a date or datetime object, returns same object type with month
  incremented
"""
def incrementByOneMonth(t):
  DAYS_31 = [1, 3, 5, 7, 8, 10]
  DAYS_30 = [4, 6, 9, 11]
  delta = datetime.timedelta(days=28)
  if (t.month in DAYS_30):
      delta = datetime.timedelta(days=30)
  elif (t.month in DAYS_31):
      delta = datetime.timedelta(days=31)
  elif (calendar.isleap(t.year)):
      delta = datetime.timedelta(days=29)
  return t + delta

"""
Brief: Gets all the data from a starting date to the day before the current day
  and writes it to a file
"""
def getFromDateToPresent(t, RTorDA, filename):
    getFromDateToDate(t, datetime.datetime.now(), RTorDA, filename)
    return

"""
Brief: Gets all the data from @start to @end for realtime or dayahead and writes
  to file @filename.
"""
def getFromDateToDate(start, end, RTorDA, filename):
    startDate = datetime.date(start.year, start.month, 1)
    while (not (startDate.year == end.year and startDate.month == end.month)):
        grabMonthData(startDate, RTorDA, filename)
        startDate = incrementByOneMonth(startDate)
    currentDate = datetime.datetime.now()
    if (startDate.year == currentDate.year and startDate.month == currentDate.month):
        while (startDate.day != end.day):
            print(startDate)
            appendDateData(startDate, RTorDA, filename)
            startDate = startDate + datetime.timedelta(days=1)
    else:
        grabMonthData(startDate, RTorDA, filename)
    return

"""
Brief: Assumes that data is given in order of hour 0 for all locations, then
  hour 1 for all locations... And creates a 2D matrix with hours as the rows and
  locations as the columns

param line A list or a comma seperated string following the format listed for
  this function
returns A two dimensional list
"""
def lineToMatrix(line):
    if (isinstance(line, str)):
        line = str.split(line, ",")
    hour = 0
    location = 0
    matrix = numpy.zeros((NUM_HOURS, NUM_USED_ZONES))
    for data in line:
      if (not data.isspace()):
        matrix[hour][location] = float(data)
        if (location == NUM_USED_ZONES - 1):
          hour += 1
        if (hour > 23):
          break
        location = (location + 1) % NUM_USED_ZONES
    return matrix

"""
Brief: Assumes data is given in order of hour 0 for all locations, then hour 1
  for all locations...on each line, and that increasing line numbers mean
  increasing days. Then returns a 3D matrix, where first index is day, then
  hour, then location
"""
def fileTo3DMatrix(filename):
    fid = open(filename, 'r')
    lines = fid.readlines()
    matrix = numpy.zeros((len(lines), NUM_HOURS, NUM_USED_ZONES))
    lineNum = 0
    for line in lines:
        matrix[lineNum] = lineToMatrix(line)
        lineNum += 1
    return matrix

"""
Returns an nx11x24 matrix of the days from @t1 to @t2 for either realtime or
  day ahead market. It also stores the data from the site in @filename
"""
def matrixofTimeframe(t1, t2, RTorDA, filename):
    getFromDateToDate(t1, t2, RTorDA, filename);
    return fileTo3DMatrix(filename)

############################## UTILS ###########################################
"""
Brief: Subtract @m2 from @m1 (m1-m2) and return the resulting matrix. We assume
 the dimensions of each matrix are the same.
"""
def matrixSubtraction(m1, m2):
    for i in range(len(m1)):
        for j in range(len(m1[0])):
            m1[i][j] = m1[i][j] - m2[i][j]
    return m1

def matrixAddition(m1, m2):
    for i in range(len(m1)):
        for j in range(len(m1[0])):
            m1[i][j] = m1[i][j] + m2[i][j]
    return m1
