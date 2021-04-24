import pandas as pd
from mortgage import Loan
import genPDF
import numpy as np

#CRITERIA TO CHANGE FOR LISTINGS
#######################
hoaFeeMax = 500
downPayment = 75000
mortgageRate = 3.0
closingCostRate = .01

fuzzyPercent = .3   #.1 would be 10 percent up or down in square footage
ageRange = 4    #4 would be 5 years up and down in age

capRateMin = -5 #minimum cap rate to filter by
compMin = 2 #min number of comps needed


listingFileName1 = 'InputFiles/Market Analysis Export.csv'
listingFileName2 = 'InputFiles/Top Producer Export.csv'
rentalFileName = 'InputFiles/rentalListings_25Miles_22102_365day_coord.csv'
#######################

def f(x):
    try:
        return np.float(x)
    except:
        return np.nan


"""""""""""""""
reads in a CSV file
"""""""""""""""
def readFile(fileName):
    data = pd.read_csv(fileName)
    return(data)


"""""""""""""""
filters listings
"""""""""""""""
def mergeTables(df1, df2):
    shortenedTable2 = df2[['MLS Number', 'Condo/Coop Fee', 'Condo/Coop Fee Freq','Remarks - Public']]
    shortenedTable2.columns = ['MLSNumber', 'Condo/Coop Fee', 'Condo/Coop Fee Freq','Remarks - Public']
    combinedDF = pd.merge(df1, shortenedTable2, on='MLSNumber')
    return(combinedDF)


"""""""""""""""
filters listings
"""""""""""""""
def filterListings(df):

    #remove non-va properties
    #df = df[df.State == "VA"]

    #calc monthly HOA fee
    df.loc[df['AssociationFeeFrequency'] == "Quarterly", ['AssociationFee']] = df['AssociationFee']/4
    df.loc[df['AssociationFeeFrequency'] == "SemiAnnually", ['AssociationFee']] = df['AssociationFee']/6
    df.loc[df['AssociationFeeFrequency'] == "Annually", ['AssociationFee']] = df['AssociationFee']/12

    #calc condo fee
    df['Condo/Coop Fee'] = df['Condo/Coop Fee'].replace( '[\$,)]','', regex=True ).replace( '[(]','-',   regex=True ).apply(f)
    df.loc[df['Condo/Coop Fee Freq'] == "Quarterly", ['Condo/Coop Fee']] = df['Condo/Coop Fee']/4
    df.loc[df['Condo/Coop Fee Freq'] == "SemiAnnually", ['Condo/Coop Fee']] = df['Condo/Coop Fee']/6
    df.loc[df['Condo/Coop Fee Freq'] == "Annually", ['Condo/Coop Fee']] = df['Condo/Coop Fee']/12
    df = df.fillna(0)
    df['hoaTotalFee'] = df['Condo/Coop Fee'] + df['AssociationFee']

    #remove high HOA fee
    #remove false low HOA fee
    df = df[df.hoaTotalFee < hoaFeeMax]
    #df = df[df.hoaTotalFee > 99]

    #calc monthly taxes
    df['TaxMonthlyTotal'] = df['TaxAnnualTotal']/12

    # monthly mortgage calculation
    intRate = mortgageRate/100
    df['List Price'] = df['List Price'].replace( '[\$,)]','', regex=True ).replace( '[(]','-',   regex=True ).apply(f)
    df = df[df['List Price'] > downPayment]
    for index,row in df.iterrows():
        df.loc[index,'MonthlyMortgage'] = Loan(principal=row['List Price']-float(downPayment), interest=intRate, term=30).monthly_payment

    #monthly total costs: hoa + mortgage + tax + insurance
    df['TotalMonthlyCosts'] = df['hoaTotalFee'].astype('float') + df['MonthlyMortgage'].astype('float') + df['TaxMonthlyTotal'].astype('float') + 25

    #calculate closing costs
    df['ClosingCosts'] = closingCostRate*df['List Price']

    return(df)


"""""""""""""""
matches comps for each listing based on criteria
"""""""""""""""
def compMatch(df1, Subdivision,Age,InteriorSqFt,Bedrooms,BathsFull):

    #filter subdivision
    df1 = df1[df1.Subdivision == Subdivision]

    #filter bedrooms
    df1 = df1[df1.Bedrooms == Bedrooms]

    #filter bathrooms +- 1
    df1 = df1[df1['BathsFull'].between(BathsFull-1, BathsFull+1)]

    #filter age +- years
    df1 = df1[df1['Age'].between(Age-ageRange, Age+ageRange)]

    #filter square foot within % range
    upperBound = InteriorSqFt+(InteriorSqFt*fuzzyPercent)
    lowerBound = InteriorSqFt-(InteriorSqFt*fuzzyPercent)
    df1 = df1[(df1['InteriorSqFt'] >= lowerBound) & (df1['InteriorSqFt'] <= upperBound)]

    #converts soldPrice str into float
    df1['SoldPrice'] = df1['SoldPrice'].replace( '[\$,)]','', regex=True ).replace( '[(]','-',   regex=True ).astype(float)

    #pack up stuff to return
    compAvg = []
    compAvg.append(df1["SoldPrice"].mean())
    compAvg.append(df1["InteriorSqFt"].mean())
    compAvg.append(df1["Age"].mean())
    compAvg.append(df1.shape[0])
    compAvg.append(df1["DOM"].mean())

    return(compAvg)



"""""""""""""""
Gets comps for each filtered property using compMatch
"""""""""""""""
def findCompsForListings(frame, df1):

    #loop thru listings and find comps
    for index,row in frame.iterrows():
        payload = compMatch(df1,row['Subdivision'],row['Age'],row['InteriorSqFt'],row['Bedrooms'],row['BathsFull'])
        frame.loc[index,'CompAvgRentRevenue'] = payload[0]
        frame.loc[index,'CompAvgSqFt'] = payload[1]
        frame.loc[index,'CompAvgAge'] = payload[2]
        frame.loc[index,'NumComps'] = payload[3]
        frame.loc[index,'CompAvgDOM'] = payload[4]

    #calculate cap rate and profit
    frame['MonthlyProfit'] = frame['CompAvgRentRevenue'] - frame['TotalMonthlyCosts']
    frame['VacancyRateCosts'] = frame['CompAvgDOM']*(frame['TotalMonthlyCosts']/30)
    frame['CapRate'] = ((frame['MonthlyProfit']*12)/(downPayment+frame['VacancyRateCosts']+frame['ClosingCosts']))*100

    return(frame)


"""""""""""""""
Calc loan burndown and appreciation of property
"""""""""""""""
def calcAppreciation(frame):
    for index,row in frame.iterrows():
        mortgagePayment =  row['MonthlyMortgage']

        initialBalance = row['List Price']-float(downPayment)

        intRate = mortgageRate/100
        monthlyInterest = float((intRate) / 12.0)

        houseValue = row['List Price']
        initialOwnershipPercent = float(downPayment)/houseValue

        amountPayed = 0
        doublePoint = 999
        months=0

        while months <= 360:

            #amount of monthly payment going towards loan baalane
            principalPayment = float(mortgagePayment) - (initialBalance * monthlyInterest)

            #keep running tally of total loan balance due
            amountPayed = amountPayed + principalPayment

            # percent of loan payed = balance left/initial borrowed amount
            percentLoanPayed = (amountPayed/initialBalance)

            # total % of house owned = (percent loan payed / percent borrowed)+percent owned by down payment
            totalOwnershipPercent = (percentLoanPayed/(1-initialOwnershipPercent))+initialOwnershipPercent

            #add 2% appreciation per year
            if months%12 == 0:
                houseValue = houseValue*1.00

            #your "net worth" in that property, find when u double ur down payment
            cashValueOwned = totalOwnershipPercent*houseValue
            if doublePoint == 999 and cashValueOwned >= downPayment*2:
                doublePoint = months

            months+=1

        frame['MonthsToDouble'] = doublePoint
        return(frame)



"""""""""""""""
Creates a dataframe with essential columns and exports it to CSV
"""""""""""""""
def exportDataframe(frame):
    final = frame[['MLSNumber','DOM','CompAvgDOM','List Price', 'City', 'Subdivision','Age','CompAvgAge', 'InteriorSqFt','CompAvgSqFt', 'Bedrooms', 'BathsFull', 'BathsHalf','NumComps', 'hoaTotalFee','MonthlyMortgage','TaxMonthlyTotal','TotalMonthlyCosts','CompAvgRentRevenue','MonthlyProfit','CapRate','VacancyRateCosts','ClosingCosts','MonthsToDouble','Remarks - Public']]
    final = final.round(2)
    final.to_csv('output.csv', sep=',')



#1) read files
file1 = readFile(listingFileName1)
file2 = readFile(listingFileName2)
rentalData = readFile(rentalFileName)

#2) merge two datasets
mergedTables = mergeTables(file1,file2)

#3) filter listings
listings = filterListings(mergedTables)

#4) find comps
payload = findCompsForListings(listings,rentalData)

#5) find loan 2x point
payload1 = calcAppreciation(payload)

#5) export columns we need
exportDataframe(payload1)

#6) create html file
genPDF.createFile(downPayment,mortgageRate)
