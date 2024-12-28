import aiohttp
import ssl
import aiohttp.typedefs
import certifi
import json
from urllib.parse import urlencode
import logging
from functools import reduce
from typing import Literal

class Async5simException(Exception):
    pass

class NoNumbersException(Async5simException):
    pass

class NoSMSException(Async5simException):
    pass

class SMSCanceledException(Async5simException):
    pass

class SMSTimeoutException(Async5simException):
    pass

class SMSFinishedException(Async5simException):
    pass

class SMSBannedException(Async5simException):
    pass

class SMSNotReceived(Async5simException):
    pass

class Async5sim:
    def __init__(self, apiKey: str, apiUrl: str = 'https://5sim.net/v1/', logger: logging.Logger = None, http_timeout: int = 15, 
                 http_proxy: aiohttp.typedefs.StrOrURL = None):
        self.logger = logger
        self.apiKey = apiKey
        self.apiUrl = apiUrl
        self.http_timeout = http_timeout
        self.http_proxy = http_proxy
        self.iso_country_dict = {
            "AF":"afghanistan", "AL":"albania", "DZ":"algeria", "AO":"angola", "AG":"antiguaandbarbuda", "AR":"argentina",
            "AM":"armenia","AW":"aruba","AU":"australia","AT":"austria","AZ":"azerbaijan","BH":"bahrain","BD":"bangladesh",
            "BB":"barbados","BY":"belarus","BE":"belgium","BJ":"benin","BT":"bhutane","BA":"bih","BO":"bolivia","BW":"botswana",
            "BR":"brazil","BG":"bulgaria","BF":"burkinafaso","BI":"burundi","KH":"cambodia","CM":"cameroon","CA":"canada",
            "CV":"capeverde","TD":"chad","CO":"colombia","CG":"congo","CR":"costarica","HR":"croatia","CY":"cyprus","CZ":"czech",
            "DK":"denmark","DM":"dominicana","TP":"easttimor","EC":"ecuador","EG":"egypt","GB":"england","GO":"equatorialguinea",
            "EE":"estonia","ET":"ethiopia","FI":"finland","FR":"france","GF":"frenchguiana","GA":"gabon","GM":"gambia",
            "GE":"georgia","DE":"germany","GH":"ghana","GI":"gibraltar","GR":"greece","GT":"guatemala","GW":"guineabissau",
            "GY":"guyana","HT":"haiti","HN":"honduras","HK":"hongkong","HU":"hungary","IN":"india","ID":"indonesia",
            "IE":"ireland","IL":"israel","IT":"italy","CI":"ivorycoast","JM":"jamaica","JO":"jordan","KZ":"kazakhstan",
            "KE":"kenya","KW":"kuwait","KG":"kyrgyzstan","LA":"laos","LV":"latvia","lS":"lesotho","LR":"liberia",
            "LT":"lithuania","LU":"luxembourg","MO":"macau","MG":"madagascar","MW":"malawi","MY":"malaysia","MV":"maldives",
            "MR":"mauritania","MU":"mauritius","MX":"mexico","MD":"moldova","MN":"mongolia","MA":"morocco","MZ":"mozambique",
            "NA":"namibia","NP":"nepal","NL":"netherlands","NC":"newcaledonia","NZ":"newzealand","NI":"nicaragua","NG":"nigeria",
            "MK":"northmacedonia","NO":"norway","OM":"oman","PK":"pakistan","PA":"panama","PG":"papuanewguinea","PY":"paraguay",
            "PE":"peru","PH":"philippines","PL":"poland","PT":"portugal","PR":"puertorico","RE":"reunion","RO":"romania",
            "RU":"russia","RW":"rwanda","KN":"saintkittsandnevis","LC":"saintlucia","VC":"saintvincentandgrenadines",
            "SV":"salvador","SA":"saudiarabia","SN":"senegal","RS":"serbia","SL":"sierraleone","SK":"slovakia","SI":"slovenia",
            "ZA":"southafrica","ES":"spain","LK":"srilanka","SR":"suriname","CH":"swaziland","SE":"sweden","TW":"taiwan",
            "TJ":"tajikistan","TZ":"tanzania","TH":"thailand","TT":"tit","TG":"togo","TN":"tunisia","TM":"turkmenistan",
            "UG":"uganda","UA":"ukraine","UY":"uruguay","US":"usa","UZ":"uzbekistan","VE":"venezuela","VN":"vietnam",
            "ZM":"zambia","ME":"montenegro","GN":"guinea"
        }
        self.country_iso_dict = {}
        for item in self.iso_country_dict.items(): 
            self.country_iso_dict[item[1]] = item[0]

    def logRequest(self, resource: str, query: dict, data: dict, response: dict):
        self.logger.debug(
            'resource: '+resource+
            ('' if query is None else ', query: '+json.dumps(query)+'}')+
            ('' if data is None else ', data: '+json.dumps(data)+'}')+
            ', response: '+json.dumps(response)+'}'
        )

    async def handleJsonResponse(self, resource, query, data, resp):
        if resp.status != 200:
            respText = await resp.text()
            if not self.logger is None:
                self.logRequest(resource, query, data, {'status':resp.status,'text':respText})
            raise Async5simException(f"Request failed:\nStatus Code: {resp.status}\nText: {respText}")
        try:
            respText = await resp.text()
            if not self.logger is None:
                self.logRequest(resource, query, data, {'status':resp.status,'text':respText})
            if respText == 'success':
                respJson = { 'success': True }
            elif respText == 'no free phones':
                raise NoNumbersException('No free phones')
            else:
                respJson = json.loads(respText)
                if resource.startswith("user/check/"):
                    status = respJson['status']
                    if 'PENDING' == status:
                        # raise SMSPendingException('Pending')
                        raise NoSMSException('Pending')
                    if 'CANCELED' == status:
                        raise SMSCanceledException('Cancelled')
                    if 'TIMEOUT' == status:
                        raise SMSTimeoutException('Timeout')
                    if 'FINISHED' == status:
                        raise SMSFinishedException('Finished')
                    if 'BANNED' == status:
                        raise SMSBannedException('Banned')
                    if 'RECEIVED' != status:
                        raise SMSNotReceived('Not received')
                    sms = respJson['sms']
                    if len(sms) == 0:
                        raise NoSMSException('No SMS')
        except ValueError as e:
            raise Async5simException(f"Request failed: {str(e)}")
        return respJson

    async def doJsonRequest(self, resource, query = None, data = None, delete = False):
        url = self.apiUrl + resource + ('' if query is None else '?' + urlencode(query))
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        conn = aiohttp.TCPConnector(ssl=ssl_context)
        headers = {"Authorization": f"Bearer {self.apiKey}"}
        async with aiohttp.ClientSession(connector=conn, headers=headers, raise_for_status=False, timeout=aiohttp.ClientTimeout(total=self.http_timeout)) as session:
            if delete:
                async with session.delete(url, json=data, timeout=self.http_timeout, proxy=self.http_proxy) as resp:
                    respJson = await self.handleJsonResponse(resource, query, data, resp)
            elif data is not None:
                async with session.post(url, json=data, timeout=self.http_timeout, proxy=self.http_proxy) as resp:
                    respJson = await self.handleJsonResponse(resource, query, data, resp)
            else:
                async with session.get(url, timeout=self.http_timeout, proxy=self.http_proxy) as resp:
                    respJson = await self.handleJsonResponse(resource, query, data, resp)
            return respJson

    async def getProfileInfo(self):
        respJson = await self.doJsonRequest('user/profile')
        return respJson

    async def getBalance(self):
        respJson = await self.doJsonRequest('user/profile')
        return {
            'balance': respJson['balance'], 
            'rating': respJson['rating'], 
            'frozen_balance': respJson['frozen_balance']
        }

    async def getOrderHistory(self, category: Literal['hosting', 'activation']):
        query = { 'category': category }
        respJson = await self.doJsonRequest('user/orders', query=query)
        return respJson

    async def getPayments(self):
        respJson = await self.doJsonRequest('user/payments')
        return respJson

    async def getMaxPrices(self):
        respJson = await self.doJsonRequest('user/max-prices')
        return respJson

    async def setMaxPrice(self, product_name: str, price: float):
        data = { 'product_name': product_name, 'price': price }
        respJson = await self.doJsonRequest('user/max-prices', data=data)
        return respJson

    async def deleteMaxPrice(self, product_name: str):
        data = { 'product_name': product_name }
        respJson = await self.doJsonRequest('user/max-prices', data=data, delete=True)
        return respJson
    
    async def getProducts(self, country: str = 'any', operator: str = 'any'):
        respJson = await self.doJsonRequest(f'guest/products/{country}/{operator}')
        return respJson
    
    async def getPrices(self, country: str = 'any', product: str = 'any'):
        query = {}
        if country and ('any' != country):
            query['country'] = country
        if product and ('any' != product):
            query['product'] = product
        respJson = await self.doJsonRequest('guest/prices', query=query)
        return respJson
    
    async def buyActivationNumber(self, country: str = 'any', operator: str = 'any', product: str = 'any',
                                  forwarding: str = None, number: str = None, reuse: str = None, voice: str = None,
                                  ref: str = None, maxPrice: str = None):
        query = {}
        if forwarding:
            query['forwarding'] = forwarding
        if number:
            query['number'] = number
        if reuse:
            query['reuse'] = reuse
        if voice:
            query['voice'] = voice
        if ref:
            query['ref'] = ref
        if maxPrice:
            query['maxPrice'] = maxPrice
        respJson = await self.doJsonRequest(f'user/buy/activation/{country}/{operator}/{product}', query=query)
        return respJson

    async def buyHostingNumber(self, country: str = 'any', operator: str = 'any', product: str = 'any'):
        respJson = await self.doJsonRequest(f'user/buy/hosting/{country}/{operator}/{product}')
        return respJson
    
    async def reuseNumber(self, product: str, number: str):
        respJson = await self.doJsonRequest(f'user/reuse/{product}/{number}')
        return respJson
    
    async def getSMS(self, id: str):
        respJson = await self.doJsonRequest(f'user/check/{id}')
        return respJson
    
    async def finishOrder(self, id: str):
        respJson = await self.doJsonRequest(f'user/finish/{id}')
        return respJson

    async def cancelOrder(self, id: str):
        respJson = await self.doJsonRequest(f'user/cancel/{id}')
        return respJson
    
    async def banOrder(self, id: str):
        respJson = await self.doJsonRequest(f'user/ban/{id}')
        return respJson
    
    async def getSMSInboxList(self, id: str):
        respJson = await self.doJsonRequest(f'user/sms/inbox/{id}')
        return respJson
    
    async def getNotifications(self, lang: Literal['en', 'ru']):
        respJson = await self.doJsonRequest(f'guest/flash/{lang}')
        return respJson
    
    async def getVendorStatistics(self):
        respJson = await self.doJsonRequest(f'user/vendor')
        return respJson
    
    async def getVendorWallets(self):
        respJson = await self.doJsonRequest(f'vendor/wallets')
        return respJson
    
    async def getVendorOrders(self, category: Literal['hosting', 'activation']):
        query = { 'category': category }                     
        respJson = await self.doJsonRequest('vendor/orders', query=query)
        return respJson

    async def getVendorPayments(self):
        respJson = await self.doJsonRequest(f'vendor/payments')
        return respJson
    
    async def createVendorWithdraw(self, receiver: str, method: str, amount: str, fee: str):
        data = { 'receiver': receiver, 'method': method, 'amount': amount, 'fee': fee }
        respJson = await self.doJsonRequest('vendor/withdraw', data=data)
        return respJson
    
    async def getCountries(self):
        respJson = await self.doJsonRequest('guest/countries')
        return respJson

    def getCountry(self, iso_country: str):
        return self.iso_country_dict[iso_country]
    
    def getIsoCountry(self, country: str, default: str):
        return self.country_iso_dict.get(country, default)
