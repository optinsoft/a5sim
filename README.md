# Async API wrapper for 5sim.net

## Installation

```bash
pip install git+https://github.com/optinsoft/a5sim.git
```

## Usage

```python
from a5sim import Async5sim
import asyncio

async def test(apiKey: str):
    a5sim = Async5sim(apiKey)
    print("getBalance\n", await a5sim.getBalance())    

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test('PUT_YOUR_API_KEY_HERE'))
```
