

Design approach

This program is comprised of the following:
- An array of asyncio coroutines that asynchronously call the patents endpoint
- A coroutine that write to a file
- Each read coroutine pulls from a pages queue that containes the required number of pages to use to pull the amount of data relative to the dates
- A writer queue that holds fetched patents in a buffer
- Once the buffer is full it flushes to storage which in my case is just writing to a file 

Why asyncio ?
- Calling this endpoint synchronously doesnt scale as we increase the range of the dates requested when each request has to wait for the next to even kick off
- We can maximise the rate at which we call the endpoint using multiple workers which is proportional to our allowed rate limit, pulling the max if 1000 records (before i hit 429s) took me roughly 3 seconds so I scaled the number of workers using timeForOneRequest / (rate_limit/60) which gives me 5 workers to use and on testing produced the fast performance as I increased the number of patents that had to be pulled. (This should be passed as an environment variable instead of being hardcoded like i have in my code)

why use a buffer for writes ?
- To reduce request overhead on the backends side and also lessen RUs
- This creates backpressure: if the writer slows down, the fetchers are forced to wait, preventing the RAM from exploding."
- If this was part of an ingestion pipeline we would want some way of having back pressure to avoid flooding the backend db with writes so bulk writes seems appropriate in this context
- It came across my mind that you would need to be conscious of the size of this buffer as its filling to avoid memory leaks

How do you handle downloading 160m patents ?
- From the test data response I estimated one patent to be about 50kb
- 160m patents then being downloaded would equate to approx 8tb 
- Downloading this on the fly from a hosted cloud instance would cause huge latency and very inneficent
- Some distributed processing like spark could be used to download the whole db on the fly 
- If were not pulling the whole db at once, an easy approach could be background jobs that run daily/weekly that pull that deltas worth of patents for indexing (which i assume is the stable approach)


Other additions I left out
- Calculating the appropriate amount of workers to use using my formula, code could be added to time 1 request of 1000 patents and then update the worker number afterwards
- I didnt add testing for my main.py since I thought my api client and the engine were the meat of this excercise, same with models













