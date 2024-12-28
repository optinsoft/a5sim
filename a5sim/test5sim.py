from .async5sim import Async5sim, Async5simException, NoSMSException
from typing import Coroutine
import logging
from aiohttp.typedefs import StrOrURL

async def testApi(apiName: str, apiRoutine: Coroutine):
    print(apiName)
    try:
        response = await apiRoutine
        print(response)
        return response
    except NoSMSException:
        print("No SMS")
    except Async5simException as e:
        print("Async5simException:", e)
    return None

async def testAsync5sim(apiKey: str, httpProxy: StrOrURL = None):
    logger = logging.Logger('test5sim')

    logger.setLevel(logging.DEBUG)

    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    log_path = './log/test.log'

    logFormatter = logging.Formatter(log_format)
    fileHandler = logging.FileHandler(log_path)
    fileHandler.setFormatter(logFormatter)
    logger.addHandler(fileHandler)

    a5sim = Async5sim(apiKey, logger=logger, http_proxy=httpProxy)

    print('--- a5sim test ---')

    await testApi("getBalance()", a5sim.getBalance())
    await testApi("getOrderHistory('activation')", a5sim.getOrderHistory('activation'))
    # await testApi("getPayments()", a5sim.getPayments())
    # await testApi("getMaxPrices()", a5sim.getMaxPrices())
    # await testApi("setMaxPrice('yahoo', 10)", a5sim.setMaxPrice('yahoo', 10))
    # await testApi("deleteMaxPrice('yahoo')", a5sim.deleteMaxPrice('yahoo'))
    # await testApi("getCountries()", a5sim.getCountries())
    country = a5sim.getCountry('BR')
    # await testApi(f"getProducts(country='{country}')", a5sim.getProducts(country=country))
    # await testApi("getPrices()", a5sim.getPrices())
    # await testApi(f"getPrices(country='{country}')", a5sim.getPrices(country=country))
    await testApi(f"getPrices(country='{country}', product='yahoo')", a5sim.getPrices(country=country, product='yahoo'))
    number = await testApi(f"buyActivationNumber(country='{country}', product='yahoo', maxPrice=10)", a5sim.buyActivationNumber(country=country, product='yahoo', maxPrice=10))
    if number:
        await testApi(f"getSMS('{number['id']}')", a5sim.getSMS(number['id']))
        await testApi(f"cancelOrder('{number['id']}')", a5sim.cancelOrder(number['id']))
    print('--- a5sim test completed ---')
