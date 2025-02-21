'''
###########################################################################################################
#
#   Trading Modules: Execute trades based on strategy signals.
#
###########################################################################################################
'''

def individual_trade_execution(ticker, port):
    '''
    Executes trade requests for a specific ticker from strategy modules.
    The trade execution process listens for trade requests and executes trades.

    :param ticker: The ticker symbol to execute trades for.
    :param port: The port to listen for trade requests on.
    :return: None
    '''
    # Better to import inside function due to multiprocessing
    from dotenv import load_dotenv
    import os, time

    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import LimitOrderRequest, GetOrdersRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.enums import QueryOrderStatus
    from alpaca.trading.models import Order

    # Load Alpaca API keys from environment variables
    load_dotenv()
    #alpaca_api_key = os.environ.get("ALPACA_API_KEY")
    #alpaca_api_secret = os.environ.get("ALPACA_API_SECRET")
    alpaca_paper_key = os.environ.get("ALPACA_PAPER_KEY")
    alpaca_paper_secret = os.environ.get("ALPACA_PAPER_SECRET")

    # Initialize the trading client
    try:
        trading_client = TradingClient(api_key=alpaca_paper_key, secret_key=alpaca_paper_secret, paper=True)
    except Exception as e:
        print(f"Error initializing trading client: {e}")
    print(f"Trading client initialized for '{ticker}'.")

    import zmq
    context = zmq.Context()
    socket = context.socket(zmq.SUB)
    socket.setsockopt(zmq.CONFLATE, 1)  # Keep only the latest message
    socket.setsockopt(zmq.SUBSCRIBE, b"")
    socket.connect(f"tcp://localhost:{port}")

    def execute_trade(ticker, buy_price, sell_price, buy_quantity):        
        # Generate the order
        try:
            position = trading_client.get_open_position(ticker)
        except Exception as e:
            if "position does not exist" in e.message:
                position = None
            else:
                print(f"TRADER WARNING: Error fetching position for '{ticker}': {e}")
                return
        if position is None and buy_price is not None:
            # No position, buy
            order_req = LimitOrderRequest(
                        symbol = ticker,
                        limit_price=buy_price,
                        qty=buy_quantity,
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.DAY
                        )
        elif position is not None and sell_price is not None:
            # Position exists, sell
            order_req = LimitOrderRequest(
                        symbol = ticker,
                        limit_price=sell_price,
                        qty=position.qty,
                        side=OrderSide.SELL,
                        time_in_force=TimeInForce.DAY
                        )
        
        # Check for existing orders for the ticker
        get_orders_data = GetOrdersRequest(
            status=QueryOrderStatus.OPEN,
            symbols=[ticker]
        )
        try:
            orders = trading_client.get_orders(filter=get_orders_data)
        except Exception as e:
            print(f"TRADER WARNING: Error fetching orders for '{ticker}', skip trading.\nError message: {e}")
            return
        if len(orders) > 1:
            # There should be at most one open order for the ticker.
            print(f"TRADER WARNING: Multiple open orders found for '{ticker}', this is bizarre! Clearing all pending orders.")
            for order in orders:
                try:
                    _ = trading_client.cancel_order_by_id(order.id)
                    print(f"Cancelled bizarre order: {order.symbol} {order.side}: {order.qty} @ {order.limit_price}")
                except Exception as e:
                    print(f"TRADER WARNING: Error cancelling bizarre order for '{ticker}', skip trading.\nError message: {e}")
                    return
        elif len(orders) == 1:
            # There is an existing order, only cancel if different from current order request
            # If we always cancel and resubmit, we might hit API rate limits
            order = orders[0]
            if order_req.side != order.side \
                or round(float(order_req.limit_price), 2) != round(float(order.limit_price), 2)\
                or round(float(order_req.qty), 2) != round(float(order.qty), 2)\
                or order_req.time_in_force != order.time_in_force:
                try:
                    _ = trading_client.cancel_order_by_id(order.id)
                except Exception as e:
                    print(f"TRADER WARNING: Error cancelling existing order for '{ticker}', skip trading.\nError message: {e}")
                    return
            else:
                # Order is the same, no need to execute
                print(f"Order already exists for {ticker}, skipping trade.")
                return None
            
        # Execute the trade
        try:
            new_order = trading_client.submit_order(order_req)
        except Exception as e:
            print(f"Error submitting order: {e}")
        return new_order
    
    try:
        last_buy, last_sell, last_qty = None, None, None
        # Main loop, continuously execute trades
        while True:
            latest_market_make = socket.recv_json()[ticker]
            got_ticker = latest_market_make['symbol']
            if got_ticker != ticker:
                raise ValueError(f"TRADER ERROR: Received unexpected ticker '{got_ticker}', expected '{ticker}'.")
            # Simulate trade execution based on market data
            price = latest_market_make['price']
            last_update = latest_market_make['time']
            buy_price = price - 1.0
            sell_price = price + 1.0
            buy_quantity = 1

            # Validate timestamp
            if time.time() - last_update > 5:
                print(f"TRADER WARNING: Stale trade request for '{ticker}', clearing all pending orders.")
                buy_price = None
                sell_price = None
            # Do no trade if prices are the same as last trade
            if buy_price == last_buy and sell_price == last_sell and buy_quantity == last_qty:
                time.sleep(0.01)
                continue
            # Execute trade
            try:
                order = execute_trade(ticker, buy_price, sell_price, buy_quantity)
            except Exception as e:
                print(f"Error executing trade for '{ticker}': {e}")
            last_buy, last_sell, last_qty = buy_price, sell_price, buy_quantity
            if isinstance(order, Order):
                print(f"Order updated: {order.symbol} {order.side}: {order.qty} @ {order.limit_price}")

    except Exception as e:
        print(f"Process encountered an error: {e}")
        raise e
    finally:
        # Clean up
        socket.close()
        context.term()
        print("Socket and context closed.")
