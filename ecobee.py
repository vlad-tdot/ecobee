# This file gets config information from a file, 
# request api token, then keep refreshing so the 
# token doesn't expire

####### Variable definition block
configFilename = 'config.json'
headers = {
    'User-Agent' : 'toaster'
}
sessionFileName = "session1.json"
dateFormat = r"%Y-%m-%d %H:%M:%S"
tick = 5 # seconds to wait in each loop


import requests, json, os
from pathlib import Path
from pprint import pprint
from datetime import datetime, timedelta
from time import sleep

def GetFromEcobeeAPI(APP_KEY, SCOPE):
    #response = requests.get('https://api.ecobee.com/authorize?response_type=ecobeePin&client_id=%s&scope=%s'% (APP_KEY, SCOPE))
    response = requests.get('https://www.theweathernetwork.com/api/weathertext/caon0696')
    pinRequest = dict()
    pinRequest['status_code'] = response.status_code
    print(type(pinRequest['status_code']))
    if (response.status_code != 200):
        print("Error, response %s" % response.status_code)
    else:
        print("Good response %s" % response.status_code)
    pinRequest['headers'] = dict(response.headers)
    print(type(pinRequest['headers']))
    #pinRequest['cookies'] = response.cookies
    #pinRequest['text']    = response.text
    pinRequest['content'] = json.loads(response.content)
    print(type(pinRequest['content']))
    print("pinrequest loaded from API request")
    # pinInfo = pinRequest.json()
    # print(pinRequest)
    return pinRequest

def WaitForPinAuth(code, APP_KEY, expiry):
    # Needed for first execution of While loop
    status = 0
    #now = datetime.now()
    while (status != 200) and (datetime.now() < expiry):
        response = requests.post('https://api.ecobee.com/token?grant_type=ecobeePin&code=%s&client_id=%s' % (code, APP_KEY), headers=headers)
        status = response.status_code
        if (status == 200):
            authInfo = response.json()
            if (authInfo['access_token']):
                debug(authInfo['access_token'])
                debug(authInfo['refresh_token'])
                timeIssued = datetime.now()
                timeExpired = timeIssued + timedelta(seconds=authInfo['expires_in'])
                authInfo['APP_KEY'] = APP_KEY
                debug("Now is %s" % timeIssued.strftime(dateFormat))
                debug("Token expires at %s" % timeExpired.strftime(dateFormat))
                #debug(authInfo)
                return(
                    {
                        "response"     : authInfo,
                        "time_issued"  : timeIssued,
                        "time_expired" : timeExpired
                    }
                )
            else:
                debug("no access token")
                debug(authInfo)
                debug(response.url)
                sleep(5)
                debug("This should never execute")
                return(
                    {
                        "error": "200_no_token",
                        "errormessage" : "Received 200, but no token was provided"
                    }
                )
        else:
            #return {'error' = response.status_code}
            if (response.status_code != 200):
                debug("Error %s; Retrying in 5 seconds" % str(response.status_code))
                sleep(5)
            elif (now > expiry):
                debug("Timed out waiting for pin authorization")
                return(
                    {
                        "error"       : "timeout",
                        "errormessage": "Timed out waiting for PIN App Authorization"
                    }
                )

def debug(message):
    print(message)        

def RefreshToken(REFRESH_TOKEN, APP_KEY):
    response = requests.post('https://api.ecobee.com/token?grant_type=refresh_token&refresh_token=%s&client_id=%s' % (REFRESH_TOKEN,APP_KEY))
    status = response.status_code
    debug('Querying URL %s, received HTTP %s' % (str(response.url), str(status)))
    if status == 200:
        authInfo = response.json()
        timeIssued = datetime.now()
        timeExpired = timeIssued + timedelta(seconds=authInfo['expires_in'])
        debug("Token issued at  %s" % timeIssued.strftime(dateFormat))
        #expireTime = datetime.now() + timedelta(seconds=authInfo['expires_in'])
        #expireTime = authInfo['time_expired']
        debug("Token expires at %s" % timeExpired.strftime(dateFormat))
        #debug(authInfo)
        #return(authInfo)
        return(
            {
                "response"     : authInfo,
                "time_issued"  : timeIssued,
                "time_expired" : timeExpired
            }
        )


def KeepRefreshed(appInfo, APP_KEY):
    i = 0
    startRenewalTime = appInfo['time_expired'] - timedelta(minutes=10)
    expireTime = appInfo['time_expired']
    while (i < 1):
        if (datetime.now() > startRenewalTime):
            debug('Current time of %s is later than start renewal time of %s' % (str(datetime.now()), str(startRenewalTime)))
            debug('Triggering token refresh')
            debug(appInfo)
            newAppInfo = RefreshToken(appInfo["response"]['refresh_token'], APP_KEY)
            appInfo = newAppInfo
            debug(appInfo)
            startRenewalTime = appInfo['time_expired'] - timedelta(minutes=45)
            WriteSessionFile(appInfo)
        timeUntilExpired = expireTime - datetime.now()
        timeUntilRefresh = startRenewalTime - datetime.now()
        print("Token expires in %s, refresh in %s" 
            % (str(timeUntilExpired), str(timeUntilRefresh)), end='\r')
        sleep(tick)




def LoadConfig(filename):
    with open(filename, "r") as configFile:
        config = json.load(configFile)
        debug("Loaded config")
    return config

def LoadSessionFile(filename):
    with open(filename, "r") as sessionFile:
        config = json.load(configFile)
        debug("Loaded config")
    return config

def WriteSessionFile(jsonContent):
    content = {
            'response' : jsonContent['response'], 
            'time_issued' : jsonContent['time_issued'].strftime(dateFormat),
            'time_expired' : jsonContent['time_expired'].strftime(dateFormat)
        }
    with open(sessionFileName, "w") as sessionFile:
        json.dump(content, sessionFile, indent=4) #, sort_keys=True)
      

# ============= MAIN BLOCK
if __name__ == "__main__":

    config = LoadConfig(configFilename)

    SCOPE   = config["SCOPE"]
    APP_KEY = config["APP_KEY"]
    debug('Appkey is %s ' % APP_KEY)
    debug("Scope is %s" % SCOPE)

    pinRequest = requests.get('https://api.ecobee.com/authorize?response_type=ecobeePin&client_id=%s&scope=%s'% (APP_KEY, SCOPE))
    debug("Requesting pin")
    debug(pinRequest.url)

    if pinRequest.status_code == 200:
        debug("pinrequest loaded from API request: %s" % pinRequest.status_code)
        debug(pinRequest.text)
        pinInfo = pinRequest.json()
        code = pinInfo['code']
        pin = pinInfo['ecobeePin']
        expiry = datetime.now() + timedelta(minutes=pinInfo['expires_in'])
        debug("Pin request expires at %s" % expiry)
        authorizedApp = WaitForPinAuth(code, APP_KEY, expiry)
        debug(authorizedApp)
        WriteSessionFile(authorizedApp)

        KeepRefreshed(authorizedApp, APP_KEY)
