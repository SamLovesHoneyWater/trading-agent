# trading-agent

A framework for highly efficient automated trading with Alpaca using ZeroMQ.

These modules run as separate parallel processes to maximize performance and minimize latency:

1. Trading Module: Handles order execution and position management through Alpaca's API
2. Strategy Module: Implements trading logic and makes a market, outputs the limit buy / sell price for each asset
3. Data Module: Manages real-time market data collection and processing

The system is designed to be easily extensible for different brokers, trading strategies, and data sources.

## Getting Started

First install dependencies. With conda, use environment.yml. With pip, use requirements.txt.

Second, go to Alpaca's website and apply for a trading account. Then obtain the secrets for your trading and paper accounts. Create a ".env" file and write your alpaca secrets and keys, following the format in .env.example.

You're good to go! Run ```python src/main.py``` to test it on your paper trade account!

## Explanations

Currently, we have a toy price generator that gradually increases the price of toy tickers.
We market make +/- $0.1 above and below the prices.

If your Alpaca account is contrained by rate limits, cap the speed of the algorithm with time.sleep() in realtime_price_publisher()

The code uses ZeroMQ extensively. Why? To minimize latency and maximize performance.
Consider when you submit $n$ orders for $n$ stocks.
The request has to go to Alpaca, their servers have to process it, etc. This takes time.
By the time the $n$ orders have gone through, the market might have already changed, and our target prices might have changed.
This is bad.
With ZeroMQ, each "slow" component of the algorithm is made independent.
Those components are separated into parallel processes that communicate with ZeroMQ.
One slow process would not block other processes, speeding up the entire application.


One drawback is that the number of ports you need grows linearly with number of tickers you want to trade.
About $2n$, to be specific.
The code puts ZeroMQ sockets on ports ranged from 13140 to 13399. Make sure those ports are clear -- they usually are, as per https://en.wikipedia.org/wiki/List_of_TCP_and_UDP_port_numbers.

## Disclaimer

This software is for educational purposes only. USE THE SOFTWARE AT YOUR OWN RISK. THE AUTHORS AND ALL AFFILIATES ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS. Do not risk money which you are afraid to lose. This code is only tested on toy examples. There might be bugs in the code - this software DOES NOT come with ANY warranty.
