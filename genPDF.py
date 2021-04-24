import pandas as pd
import numpy as np
from bs4 import BeautifulSoup

def readFile(fileName):
    data = pd.read_csv(fileName)
    return(data)

def createFile(downPayment, interestRate):

    #read file
    df = readFile("output.csv")

    downPayment_str = "{:,}".format(downPayment)
    interestRate_str = str(interestRate)+'% APR'

    #make object per item
    for index,row in df.iterrows():
        mlsNumber = row['MLSNumber']
        city = row['City']
        listPrice = "{:,}".format(row['List Price'])
        downPaymentPercent = str(int((downPayment/row['List Price'])*100))+'%'
        age = str(row['DOM'])+ ' Day(s)'
        size = str(row['InteriorSqFt'])+" Sq Ft"
        rooms = str(row['Bedrooms'])+" Bed / "+str(row['BathsFull'])+" Bath"

        hoaMonthly = "{:,}".format(row['hoaTotalFee'])
        mortgageMonthly = "{:,}".format(row['MonthlyMortgage'])
        taxMonthly = "{:,}".format(row['TaxMonthlyTotal'])
        rentalIncome = "{:,}".format(row['CompAvgRentRevenue'])
        monthlyProfit = "{:,}".format(row['MonthlyProfit'])
        capRate = str(row['CapRate']) + '%'

        compSize = str(row['CompAvgSqFt'])+" Sq Ft"
        compAge = str(int(row['CompAvgAge']))
        numComps = str(int(row['NumComps']))

        vacancyRateCosts = "{:,}".format(row['VacancyRateCosts'])
        closingCosts = "{:,}".format(row['ClosingCosts'])
        totalCashOnHand = "{:,}".format(row['VacancyRateCosts']+row['ClosingCosts']+downPayment)
        compAvgDOM = str(row['CompAvgDOM'])+' Day(s)'

        remarks = row['Remarks - Public']
        subdivision = row['Subdivision']

    soup = BeautifulSoup(open('template.html'), 'html.parser')
    #main section with images
    maindiv = soup.findAll("div", {"class": "layer w-100"})
    new_tag = soup.new_tag('img', src='https://xomesearch.propertiescdn.com/ListingImages/mdbmls/images/0/0/'+mlsNumber+'.jpg', width=500)
    maindiv[0].append(new_tag)
    maindiv[0].append(remarks)



    #property info section
    h6 = soup.findAll("h6", {"class": "lh-1"})
    h6[0].string.replace_with('Property Info - '+mlsNumber) #mls number
    h5 = soup.find_all('h5')
    h5[0].string.replace_with('$'+listPrice) #list price
    h5[1].string.replace_with(age) #days on market
    h5[2].string.replace_with(city) #city
    h5[3].string.replace_with(size) #size
    h5[4].string.replace_with(rooms) #rooms
    h5[5].string.replace_with('1990') #year built

    #assumptions section
    peerDivs = soup.findAll("div", {"class": "peer peer-greed"})
    percentSpansBlue = soup.findAll("span", {"class": "d-ib lh-0 va-m fw-600 bdrs-10em pX-15 pY-15 bgc-blue-50 c-blue-500"})
    percentSpansPurple = soup.findAll("span", {"class": "d-ib lh-0 va-m fw-600 bdrs-10em pX-15 pY-15 bgc-purple-50 c-purple-500"})
    peerDivs[0].string.replace_with('$'+downPayment_str) #down payment
    percentSpansBlue[0].string.replace_with(downPaymentPercent) #down payment %
    percentSpansBlue[1].string.replace_with(interestRate_str) #mortgage rate %
    percentSpansPurple[0].string.replace_with(numComps+' Found') #num comps found

    #cash on hand section
    td = soup.find_all('td')
    td[1].string.replace_with('$'+downPayment_str) #down payment
    td[3].string.replace_with('$'+vacancyRateCosts) #avg vacancy
    td[5].string.replace_with('$'+closingCosts) #closing costs
    totalText = soup.findAll("span", {"class": "fsz-def fw-600 mR-10 c-grey-800"})
    totalText[0].string.replace_with('$'+totalCashOnHand) #total cash on hand

    #monthly costs section
    td[7].string.replace_with('$'+hoaMonthly) #hoa fee total
    td[9].string.replace_with('$'+mortgageMonthly) #mortgage
    td[11].string.replace_with('$'+taxMonthly) #taxes
    td[13].string.replace_with('$'+rentalIncome) #revenue
    td[15].string.replace_with('$'+monthlyProfit) #profit
    totalText[1].string.replace_with(capRate)

    #comp section
    td[17].string.replace_with(subdivision) #subdivision
    td[19].string.replace_with(compSize) #avg size
    td[21].string.replace_with(compAge) #avg year built
    td[23].string.replace_with(compAvgDOM) #avg vacancy


    with open("website/src/index.html", "w") as file:
        file.write(str(soup))
