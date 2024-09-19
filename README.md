A 3D visualizer of the Kraken crypto platform real-time order book, with aggregated volume of bids and asks for `book_depth` specified order book depth.  Made using the Kraken Websocket API but does not require API key authorization as access is read-only.
Thie gif below is for ETH/USD with book depth of 25.

![ethdown](https://github.com/user-attachments/assets/bc9f4bbc-2ff6-4c0a-8c03-1e8f1c514db8)




### Usage:

Specify `ticker` name and `book depth` (10, 25, 100, 500, 1000) and call 
```python
asyncio.get_event_loop().run_until_complete(main())
```
