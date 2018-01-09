import pandas as pd
import re
import numpy as np
import sys
import math
import datetime
import matplotlib.pyplot as plt
import urllib.request
import os
import ssl

ssl._create_default_https_context = ssl._create_unverified_context


class TrendStrat:
    def __init__(self,closeSign=1, symbol="AAPL", stdevRoll=30,apikey="PT1IPJSO9WO8TW7N", interval="daily", adjusted="Y", stratPeriod="52w",startDate="2010-01-04", holdingPeriod="6m", tickerList="DJticker.csv", winnerQuantile=0.2,loserQuantile=0.2, benchmark="SPY"):
        self.symbol = symbol
        self.apikey = apikey
        self.interval = interval
        self.adjusted = adjusted
        self.stratPeriod = stratPeriod
        self.startDate = startDate
        self.holdingPeriod = holdingPeriod
        self.benchmark = benchmark
        tickerList = pd.read_csv(tickerList)
        tickerList[self.benchmark] = []
        self.tickerList = tickerList
        self.winnerQuantile = winnerQuantile
        self.loserQuantile = loserQuantile
        self.stdevRoll=stdevRoll
        ##Decide the endDate
        match = re.match(r"([0-9]+)([a-z]+)", self.holdingPeriod, re.I)
        num = int(match.group(1))
        word = match.group(2)
        if word == "m":
            days = 30 * num
        else:
            days = num
        tempDate = datetime.datetime.strptime(self.startDate, "%Y-%m-%d")
        self.endDate = tempDate + datetime.timedelta(days=days)
        self.endDate = self.endDate.strftime("%Y-%m-%d")
        self.closeSign=closeSign
    def deletePrevData(self):
        cwd = os.getcwd()
        for ticker in self.tickerList:
            fileName = cwd + "\\" + "daily_adjusted_" + ticker + ".csv"
            if os.path.isfile(fileName):
                os.remove(fileName)
        return
    def downloadData(self):
        try:
            cwd = os.getcwd()
            if self.interval == "daily":
                if self.adjusted == "N":
                    i = 0
                    for ticker in self.tickerList:
                        fileName = cwd + "\\" + "daily_unadjusted_" + ticker + ".csv"
                        if os.path.isfile(fileName) == False:
                            url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=" + ticker + "&apikey=" + self.apikey + "&datatype=csv&outputsize=full"
                            urllib.request.urlretrieve(url, fileName)
                        i += 1
                        sys.stdout.write(
                            '\r Dowloading Data: %.2f%%-%s' % (((i * 100 / (len(self.tickerList.columns)))), ticker))
                        sys.stdout.flush()
                else:
                    i = 0
                    for ticker in self.tickerList:
                        fileName = cwd + "\\" + "daily_adjusted_" + ticker + ".csv"
                        if os.path.isfile(fileName) == False:
                            url = "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol=" + ticker + "&apikey=" + self.apikey + "&datatype=csv&outputsize=full"
                            urllib.request.urlretrieve(url, fileName)
                        i += 1
                        sys.stdout.write(
                            '\r Dowloading Data: %.2f%%-%s' % (((i * 100 / (len(self.tickerList.columns)))), ticker))
                        sys.stdout.flush()
            else:
                i = 0
                for ticker in self.tickerList:
                    fileName = cwd + "intraday_" + self.interval + "_" + ticker + ".csv"
                    if os.path.isfile(fileName) == False:
                        url = "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=" + ticker + "&interval=" + self.interval + "&apikey=" + self.apikey + "&datatype=csv&outputsize=full"
                        urllib.request.urlretrieve(url, fileName)
                    i += 1
                    sys.stdout.write(
                        '\r Dowloading Data: %.2f%%-%s' % (((i * 100 / (len(self.tickerList.columns)))), ticker))
                    sys.stdout.flush()
        except:
            print ("Reconnecting")
            TrendStrat.downloadData(self)
        return

    def readData(self):
        cwd = os.getcwd()
        data = {}
        if self.interval == "daily":
            if self.adjusted == "N":
                for ticker in self.tickerList:
                    fileName = cwd + "\\" + "daily_unadjusted_" + ticker + ".csv"
                    data[ticker] = pd.read_csv(fileName)
                    data[ticker] = data[ticker].set_index('timestamp').sort_index()
            else:
                for ticker in self.tickerList:
                    fileName = cwd + "\\" + "daily_adjusted_" + ticker + ".csv"
                    data[ticker] = pd.read_csv(fileName)
                    data[ticker] = data[ticker].set_index('timestamp').sort_index()
        else:
            for ticker in self.tickerList:
                fileName = cwd + "intraday_" + self.interval + "_" + ticker + ".csv"
                data[ticker] = pd.read_csv(fileName)
                data[ticker] = data[ticker].set_index('timestamp').sort_index()
        return data

    def generateData(self, data):
        currentToHighRatio = []
        high = []
        dailyReturn=[0]
        ############determin the window width###################
        match = re.match(r"([0-9]+)([a-z]+)", self.stratPeriod, re.I)
        num = int(match.group(1))
        word = match.group(2)
        ##We can only test "min" period with minutely data
        if word == "min" and self.interval != "1min":
            print("Have to use minutely data")
            return None
        if word == "w":
            windowWidth = 5 * num
        if word == "d" or word == "min":
            windowWidth = num
        ##############################################
        rawData = data
        if self.adjusted == "Y":
            if windowWidth<len(rawData):
                for m in range(windowWidth):
                    high.append(rawData[0:m]["adjusted_close"].max())
                    currentToHighRatio.append(rawData['adjusted_close'][m] / rawData[0:m]["adjusted_close"].max())
                for j in range(windowWidth, len(rawData)):# the data after the first 52W or so
                    rollWindow = rawData[j - windowWidth + 1:j + 1]
                    high.append(rollWindow["adjusted_close"].max())
                    currentToHighRatio.append(rawData['adjusted_close'][j] / rollWindow["adjusted_close"].max())
            else:
                for m in range(len(rawData)):
                    high.append(rawData[0:m]["adjusted_close"].max())
                    currentToHighRatio.append(rawData['adjusted_close'][m] / rawData[0:m]["adjusted_close"].max())
            for i in range(1,len(rawData)):
                dailyReturn.append(rawData["adjusted_close"][i]/rawData["adjusted_close"][i-1]-1)
            del rawData['dividend_amount']
            del rawData['split_coefficient']
        else:
            if windowWidth<len(rawData):
                for m in range(windowWidth):
                    high.append(rawData[0:m]["high"].max())
                    currentToHighRatio.append(rawData["high"][m] / rawData[0:m]["high"].max())
                for j in range(windowWidth, len(rawData)):
                    rollWindow = rawData[j - windowWidth + 1:j + 1]
                    high.append(rollWindow["high"].max())
                    currentToHighRatio.append(rawData['close'][j] / rollWindow["high"].max())
            else:
                for m in range(len(rawData)):
                    high.append(rawData[0:m]["high"].max())
                    currentToHighRatio.append(rawData["high"][m] / rawData[0:m]["high"].max())
            for i in range(1,len(rawData)):
                dailyReturn.append(rawData["high"][i]/rawData["high"][i-1]-1)
        colName = self.stratPeriod + "_high"
        rawData[colName] = np.array(high)
        rawData["price/high"] = np.array(currentToHighRatio)
        rawData["daily_return"]=np.array(dailyReturn)
        return rawData

    def generateAllTickers(self, data):
        finalData = {}
        i = 0
        for ticker in self.tickerList:
            tempData = data[ticker]
            finalData[ticker] = TrendStrat.generateData(self, data=tempData)
            i += 1
            sys.stdout.write('\r Generating Data: %.2f%%-%s' % (((i * 100 / (len(self.tickerList.columns)))), ticker))
            sys.stdout.flush()
        return finalData

    def backTestWinnerLoser(self, data):#only suitable for those stocks which all have adequate data to support the start date
        startDatePriceList = []
        for ticker in self.tickerList.columns[:-1]:
            if self.startDate not in data[ticker].index.values:  # Judge whether the start date is valid.This requires that every stock has a valid data on that date. Not practical.
                print ("Start Date is not a valid trading day")
                return
            else:
                startDatePriceList.append(
                    data[ticker].loc[self.startDate])  # return the price of all the stocks on Start data
        priceForStartDate = pd.DataFrame(startDatePriceList)
        priceForStartDate['ticker'] = np.array(list(self.tickerList.columns[:-1]))
        priceForStartDate = priceForStartDate.set_index('ticker')
        priceForStartDate['price/high'] = priceForStartDate['price/high'].astype(float)
        ##find the winner and loser portfolio of that day
        winner = priceForStartDate.nlargest(math.floor(len(self.tickerList.columns) * self.winnerQuantile),
                                            'price/high')
        loser = priceForStartDate.nsmallest(math.floor(len(self.tickerList.columns) * self.loserQuantile), 'price/high')
        winnerPortfolio = {}
        loserPortfolio = {}
        winnerTicker = {"winnerTicker": winner.index.values}
        loserTicker = {"loserTicker": loser.index.values}
        for i in range(20):
            if self.endDate not in data[ticker].index.values:  # Judge whether the end date is valid
                tempDate = datetime.datetime.strptime(self.endDate, "%Y-%m-%d")
                self.endDate = tempDate - datetime.timedelta(days=1)
                self.endDate = self.endDate.strftime("%Y-%m-%d")
        for ticker in winner.index.values:
            cumReturn = []
            winnerPortfolio[ticker] = data[ticker][self.startDate:self.endDate]
            for index in winnerPortfolio[ticker].index.values:
                cumReturn.append((winnerPortfolio[ticker].loc[index, 'adjusted_close'] - winnerPortfolio[ticker].loc[
                    self.startDate, 'adjusted_close']) / winnerPortfolio[ticker].loc[self.startDate, 'adjusted_close'])
            winnerPortfolio[ticker]['cumReturn'] = np.array(cumReturn)
        for ticker in loser.index.values:
            cumReturn = []
            loserPortfolio[ticker] = data[ticker][self.startDate:self.endDate]
            for index in loserPortfolio[ticker].index.values:
                cumReturn.append((loserPortfolio[ticker].loc[index, 'adjusted_close'] - loserPortfolio[ticker].loc[
                    self.startDate, 'adjusted_close']) / loserPortfolio[ticker].loc[self.startDate, 'adjusted_close'])
            loserPortfolio[ticker]['cumReturn'] = np.array(cumReturn)
        cumReturn = []
        benchmark = data[self.benchmark][self.startDate:self.endDate]
        for index in benchmark.index.values:
            cumReturn.append((data[self.benchmark].loc[index, 'adjusted_close'] - data[self.benchmark].loc[
                self.startDate, 'adjusted_close']) / data[self.benchmark].loc[self.startDate, 'adjusted_close'])
        benchmark['cumReturn'] = np.array(cumReturn)
        portfolio = {**winnerTicker, **loserTicker, **winnerPortfolio, **loserPortfolio}
        portfolio[self.benchmark] = benchmark
        # print("Finish testing!")
        # print("Get the winner ticker by your_variables[\"winnerTicker\"] and loser ticker by your_variables[\"loserTicker\"]")
        # print("Get individual data by your_vatiables[winner/loserticker]")
        return portfolio

    def plotResultWinnerLoser(self, portfolio):
        if self.winnerQuantile != 0:
            winnerTickerWithBenchmark = portfolio['winnerTicker'].tolist()
            winnerTickerWithBenchmark.append(self.benchmark)
            for ticker in winnerTickerWithBenchmark:
                plt.plot(portfolio[ticker]['cumReturn'])
            plt.xticks(visible=False)
            plt.title("Winner Portfolio")
            plt.legend(winnerTickerWithBenchmark)
            axes = plt.gca()
            axes.set_ylim([-0.25, 0.25])
            plt.grid()
            plt.show()
        if self.loserQuantile != 0:
            loserTickerWithBenchmark = portfolio['loserTicker'].tolist()
            loserTickerWithBenchmark.append(self.benchmark)
            for ticker in loserTickerWithBenchmark:
                plt.plot(portfolio[ticker]['cumReturn'])
            plt.xticks(visible=False)
            plt.title("Loser Portfolio")
            plt.legend(loserTickerWithBenchmark)
            axes = plt.gca()
            axes.set_ylim([-0.25, 0.25])
            plt.grid()
            plt.show()
        print("Strategy's looking-back period is {}".format(self.stratPeriod))
        print("Strategy's holding period is {}".format(self.holdingPeriod))
        print("Position's open date is {}".format(self.startDate))
        print("Position's close date is {}".format(self.endDate))
        return
    def generateAnnualStdDev(data):
        return np.std(data)*((252/(len(data)))**(1/2))
    def MDD(data):
        highmark=0
        maxDrawDown=0
        for i in range(len(data)):
            if data[i]>highmark:
                highmark=data[i]
            if (data[i]-highmark)/highmark<maxDrawDown:
                maxDrawDown=(data[i]-highmark)/highmark
        return maxDrawDown
    def sharpeRatio(data):
        return 2*np.mean(np.array(data))/np.std(np.array(data))
    def informationRatio(portfolio,benchmark):
        return (np.mean(np.array(portfolio))-np.mean(np.array(benchmark)))/np.std(np.array(portfolio))
    def backtestAllTime(self,data):
        ##########get the stop loss signal#####
        numOfStdDev = self.closeSign
        allTimeBacktest={}
        i=0
        pathName=os.getcwd()+"\\"+"individualTestResult"
        if not os.path.exists(pathName):
            os.makedirs(pathName)
        for ticker in self.tickerList.columns[:-1]:# exclude benchmark
            positionStatus=0
            cumReturn=[0]
            highMark=[]
            dailyReturn=[]
            drawDown=[]
            date=[]
            for index in data[self.benchmark].index.values:# set benchmark trading days as the days to look for stocks
                ###########generate stddev based on data before open position#####
                if index in data[ticker].index.values:
                    if len(data[ticker][:index])>self.stdevRoll:
                        existedData=data[ticker][:index].tail(self.stdevRoll)
                    else:
                        existedData=data[ticker][:index]
                    curStdDev=TrendStrat.generateAnnualStdDev(existedData)["daily_return"]
                if index in data[ticker].index.values and data[ticker]["price/high"][index]>=1 and positionStatus==0:# signal to open position
                    openPrice=data[ticker]["adjusted_close"][index]
                    curHighMark=0
                    positionStatus=1
                    cumReturnSingleTime=[0]
                if index in data[ticker].index.values and positionStatus==1:
                    curDailyReturn=data[ticker]["adjusted_close"][index]/data[ticker]["adjusted_close"][data[ticker].index.get_loc(index)-1]-1
                    curCumReturn=(curDailyReturn+1)*(cumReturn[-1]+1)-1
                    curCumReturnSingleTime=(curDailyReturn+1)*(cumReturnSingleTime[-1]+1)-1
                    dailyReturn.append(curDailyReturn)
                    cumReturn.append(curCumReturn)
                    cumReturnSingleTime.append(curCumReturnSingleTime)
                    date.append(index)
                    if curCumReturnSingleTime>curHighMark:
                        curHighMark=curCumReturnSingleTime
                    highMark.append(curHighMark)
                    curDrawDown=curCumReturnSingleTime-curHighMark
                    drawDown.append(curDrawDown)
                    if (curCumReturnSingleTime-curHighMark)<(-numOfStdDev*curStdDev):
                        positionStatus=0
            allTimeBacktest[ticker]= pd.DataFrame()
            allTimeBacktest[ticker]["timestamp"]=np.array(date)
            allTimeBacktest[ticker]["dailyReturn"]=np.array(dailyReturn)
            allTimeBacktest[ticker]["cumReturn"]=np.array(cumReturn[1:])
            allTimeBacktest[ticker]=allTimeBacktest[ticker].set_index('timestamp').sort_index()
            fileName=pathName+"\\"+ticker+".csv"
            allTimeBacktest[ticker].to_csv(fileName)
            i+=1
            sys.stdout.write('\r Backtesting: %.2f%%-%s' % (((i * 100 / (len(self.tickerList.columns)-1))), ticker))
            sys.stdout.flush()
        return allTimeBacktest
    def generateHoldingLogFullPosition(self,rawData,backtestResult):
        holdingList={}
        curCumReturn=[]
        dailyReturn=[]
        cumReturn=[0]
        date=[]
        for index in rawData[self.benchmark].index.values:
            curDailyReturn=[]
            dailyHoldingList=[]
            for ticker in self.tickerList.columns[:-1]:
                if index in backtestResult[ticker].index.values:
                    dailyHoldingList.append(ticker)
                    curDailyReturn.append(backtestResult[ticker]["dailyReturn"][index])
            date.append(index)
            holdingList[index]=pd.DataFrame(dailyHoldingList)
            if len(holdingList[index])!=0:
                dailyReturn.append(np.average(np.array(curDailyReturn)))
            else:
                dailyReturn.append(0)
        allTimeReturn=pd.DataFrame()
        allTimeReturn["timestamp"]=np.array(date)
        allTimeReturn["dailyReturn"]=np.array(dailyReturn)
        allTimeReturn["cumReturn"]=(1 + allTimeReturn.dailyReturn).cumprod() - 1
        allTimeReturn=allTimeReturn.set_index('timestamp').sort_index()
        holdingList["return"]=allTimeReturn
        pathName=os.getcwd()+"\\"+"holdingLog"
        if not os.path.exists(pathName):
            os.makedirs(pathName)
        for key in holdingList.keys():
            fileName=pathName+"\\"+key+".csv"
            holdingList[key].to_csv(fileName)
        return holdingList
    def generateHoldingLogPortionalPosition(self,rawData,backtestResult):
        holdingList={}
        curCumReturn=[]
        dailyReturn=[]
        cumReturn=[0]
        date=[]
        weightToEachStock=1/(len(list(self.tickerList))-1)
        for index in rawData[self.benchmark].index.values:
            curDailyReturn=[]
            dailyHoldingList=[]
            for ticker in self.tickerList.columns[:-1]:
                if index in backtestResult[ticker].index.values:
                    dailyHoldingList.append(ticker)
                    curDailyReturn.append(backtestResult[ticker]["dailyReturn"][index])
            date.append(index)
            holdingList[index]=pd.DataFrame(dailyHoldingList)
            if len(holdingList[index])!=0:
                dailyReturn.append(weightToEachStock*(sum(curDailyReturn)))
            else:
                dailyReturn.append(0)
        allTimeReturn=pd.DataFrame()
        allTimeReturn["timestamp"]=np.array(date)
        allTimeReturn["dailyReturn"]=np.array(dailyReturn)
        allTimeReturn["cumReturn"]=(1 + allTimeReturn.dailyReturn).cumprod() - 1
        allTimeReturn=allTimeReturn.set_index('timestamp').sort_index()
        holdingList["return"]=allTimeReturn
        pathName=os.getcwd()+"\\"+"holdingLog"
        if not os.path.exists(pathName):
            os.makedirs(pathName)
        for key in holdingList.keys():
            fileName=pathName+"\\"+key+".csv"
            holdingList[key].to_csv(fileName)
        return holdingList
    def generateHoldingLogIncreasingPosition(self,rawData,backtestResult):
        holdingList={}
        marketValue=[1000000]
        marketValueEachStock={}
        dailyReturn=[]
        date=[]
        cumReturn=[]
        for ticker in self.tickerList.columns[:-1]:
            marketValueEachStock[ticker]=marketValue[-1]/(len(list(self.tickerList))-1)
        for ticker in self.tickerList.columns[:-1]:
            backtestResult[ticker]["positionFlag"]=0
            for index in rawData[self.benchmark].index.values:
                if index in backtestResult[ticker].index.values:
                    if rawData[self.benchmark].index[rawData[self.benchmark].index.get_loc(index)-1] not in backtestResult[ticker].index.values:
                        backtestResult[ticker]["positionFlag"][index]=1                
        for index in rawData[self.benchmark].index.values:
            dailyHoldingList=[]
            for ticker in self.tickerList.columns[:-1]:
                if index in backtestResult[ticker].index.values:
                    dailyHoldingList.append(ticker)
            date.append(index)
            holdingList[index]=pd.DataFrame(dailyHoldingList)
        for index in rawData[self.benchmark].index.values:
            for ticker in self.tickerList.columns[:-1]:
                if index in backtestResult[ticker].index.values:
                    if backtestResult[ticker]["positionFlag"][index]==0:
                        marketValueEachStock[ticker]=marketValueEachStock[ticker]*(1+backtestResult[ticker]["dailyReturn"][index])
                    if backtestResult[ticker]["positionFlag"][index]==1:
                        marketValueEachStock[ticker]=marketValue[-1]/(len(list(self.tickerList))-1)
                        marketValueEachStock[ticker]=marketValueEachStock[ticker]*(1+backtestResult[ticker]["dailyReturn"][index])
            marketValue.append(sum(marketValueEachStock.values()))
            dailyReturn.append(marketValue[-1]/marketValue[-2]-1)
            cumReturn.append(marketValue[-1]/marketValue[0])
        allTimeReturn=pd.DataFrame()
        allTimeReturn["date"]=np.array(date)
        allTimeReturn["dailyReturn"]=np.array(dailyReturn)
        allTimeReturn["cumReturn"]=np.array(cumReturn)
        allTimeReturn=allTimeReturn.set_index('date').sort_index()
        holdingList["return"]=allTimeReturn
                   
        pathName=os.getcwd()+"\\"+"holdingLog"
        if not os.path.exists(pathName):
            os.makedirs(pathName)
        for key in holdingList.keys():
            fileName=pathName+"\\"+key+".csv"
            holdingList[key].to_csv(fileName)
        return holdingList