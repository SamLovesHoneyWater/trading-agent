'''
###########################################################################################################
#
#   Data Modules: Get stock prices, display prices, etc.
#
###########################################################################################################
'''

def realtime_price_publisher(ticker, port):
    '''
    A real-time price publisher for a given ticker.
    The publisher sends the latest price data to a socket.

    :param ticker: The ticker symbol to publish data for.
    :param port: The port to publish data to.
    :return: None
    '''
    # Better to import inside function due to multiprocessing
    import zmq, time
    
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{port}")

    def get_realtime_price(i):
        price = 100.0 + i/10
        return {
            'symbol': ticker,
            'price': price,
            'time': time.time()
        }

    try:
        # Main loop, continuously send latest price data
        i = 0
        while True:
            time.sleep(0.01)
            i += 1
            latest_price = get_realtime_price(i)
            socket.send_json(latest_price)  # Send latest data
    except Exception as e:
        print(f"Process encountered an error: {e}")
        raise e
    finally:
        # Clean up
        socket.close()
        context.term()
        print("Socket and context closed.")

def realtime_prices_manager(tickers, consume_ports, port):
    '''
    Manages real-time price publishers for multiple tickers.
    The manager consumes the latest price data for each ticker and sends it to an aggregate publisher.
    Design note: The choice to separate individual publishers is aimed at decreasing latency in price updates.

    :param tickers: A list of ticker symbols to manage.
    :param consume_ports: A list of ports to consume data from.
    :param port: The port to publish aggregated data to.
    :return: None
    '''
    # Better to import inside function due to multiprocessing
    import zmq, time
    context = zmq.Context()

    # Create a socket to publish aggregated data
    publish_socket = context.socket(zmq.PUB)
    publish_socket.bind(f"tcp://*:{port}")

    # Create sockets to consume data from each ticker
    consume_sockets = []
    for consume_port in consume_ports:
        socket = context.socket(zmq.SUB)
        socket.setsockopt(zmq.CONFLATE, 1)  # Keep only the latest message
        socket.setsockopt(zmq.SUBSCRIBE, b"")
        socket.connect(f"tcp://localhost:{consume_port}")
        consume_sockets.append(socket)
    
    def get_aggregated_prices():
        aggregated_prices = {}
        for socket in consume_sockets:
            latest_price = socket.recv_json()
            aggregated_prices[latest_price['symbol']] = latest_price
        return aggregated_prices
    
    try:
        # Main loop, continuously aggregate latest price data
        while True:
            latest_prices = get_aggregated_prices()
            publish_socket.send_json(latest_prices)  # Send aggregated data
            time.sleep(1)  # Delay
    except Exception as e:
        print(f"Process encountered an error: {e}")
        raise e
    finally:
        # Clean up
        for socket in consume_sockets:
            socket.close()
        publish_socket.close()
        context.term()
        print("Sockets and context closed.")

def realtime_price_display_consumer(tickers, port):
    '''
    A real-time price consumer that subscribes to an aggregated price publisher and prints the latest prices.
    
    :param tickers: A list of ticker symbols to display prices for.
    :param port: The port to consume data from.
    :return: None
    '''
    # Better to import inside function due to multiprocessing
    import zmq, time
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.CONFLATE, 1)  # Keep only the latest message
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    socket.connect(f"tcp://localhost:{port}")

    def print_realtime_price(prices):
        time.sleep(1)
        #return
        for ticker in tickers:
            price_data = prices.get(ticker)
            if price_data:
                print(f"'{ticker}': {price_data['price']} ({price_data['time']})")
        print()

    try:
        # Main loop, continuously display latest price data
        while True:
            latest_prices = socket.recv_json()
            print_realtime_price(latest_prices)
    except Exception as e:
        print(f"Process encountered an error: {e}")
        raise e
    finally:
        # Clean up
        socket.close()
        context.term()
        print("Socket and context closed.")
