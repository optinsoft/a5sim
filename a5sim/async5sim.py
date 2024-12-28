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
