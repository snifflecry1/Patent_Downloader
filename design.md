Right now the design is as follows:
- Use async requests to batch requests:
    Each request takes a page with certain amount of items
    Use semaphore to limit the number of concurrent request
    Make sure this number is with in rate limits for api


    Tasks
    1. Define a dataclass for FastAPI to store patent data
    2. Define a function to ping datasource for max documents - Done
    3. Define a shared rate limiter worker queue can use - Done
    3. Define a function that sets up workers based on num docs
        - For output to screen do we want to store this in a generator ? (Potentially)
        - I think it would be more appropriate for the excercise if we just save to file
    4. Testing for each function




- Figure out the time it would take to download 160m with this method
    Explore other avenues to acheive this faster e.g Distributed processing etc


- We need to batch pulled items instead of writing individually to storage
    Figure out a suitable batch amount and then write flush logic

    1. Define a mock function that would batch patents together to do a batch insert and minimise requests count to db
    2. Testing ?



Notes
Seems to be a bug when requesting any data from specifically page 4 across runs, if its less than 4 pages the program finishes in time if its 4 or more, it always wait for the timeout because page 4 doesnt seem to finish or something

optimal workers is time for 1 batch request/requestpersecond