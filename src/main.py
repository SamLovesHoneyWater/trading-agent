###############################################################################
#                                                                             #
#        Framework for data/trade/strategy modularization                     #
#        with ZeroMQ and multiprocessing                                      #
#                                                                             #
#        By SamLovesHoneyWater                                                #
#        Feb 21, 2025                                                         #
#                                                                             #
###############################################################################

import time
import multiprocessing

from tradingModule import individual_trade_execution
from dataModule import realtime_price_publisher, realtime_prices_manager, realtime_price_display_consumer

class ChildrenProcessesData:
    '''
    A class to store data about child processes and ports.
    Design note: this method-less class makes it easy to pass around global information about child processes.
    
    :param initial_port: The initial port number to start assigning ports from.
    :param max_port: The maximum port number allowed.
'''
    def __init__(self, initial_port=13140, max_port=13399):
        self.next_free_port = initial_port
        self.max_port = max_port
        self.child_processes = []

        if self.next_free_port > self.max_port:
            raise ValueError(f"Initial port {initial_port} exceeds maximum port {max_port}.")

def register_process_with_port(target=None, args=None, need_port=False, cpd=None):
    '''
    Registers a process and assigns a specific port for the process to use.
    Always use this function to create a new process to ensure proper management of child processes.
    
    :param target: The target function to run in the process.
    :param args: A tuple of arguments to pass to the target function.
    :param new_port: If True, assigns a new port to the process. If False, d
    :param cpd: The ChildrenProcessesData object that tracks all processes and ports.

    :return: The process object and the port assigned to the process.
    '''
    if target is None or args is None or cpd is None:
        raise ValueError("register_process_with_port() requires target, args, and cpd arguments.")
    if not isinstance(cpd, ChildrenProcessesData):
        raise ValueError("cpd must be an instance of ChildrenProcessesData.")
    if need_port:
        # Assign a free port and increment the next free port
        if cpd.next_free_port > cpd.max_port:
            raise Exception(f"No more ports available, exceeded maximum allowed port number {cpd.max_port}.")
        new_port = cpd.next_free_port
        args_w_port = args + (new_port,)  # Add the port to the arguments
        cpd.next_free_port += 1
    else:
        new_port = None
        args_w_port = args

    # Create the new process
    process = multiprocessing.Process(target=target, args=args_w_port)

    # Add the process to the list of child processes
    cpd.child_processes.append(process)
    return process, new_port


if __name__ == '__main__':
    tickers = ['AAPL', 'GOOGL', 'AMZN', 'MSFT', 'TSLA']
    child_processes_data = ChildrenProcessesData()

    # Create realtime price processes for each ticker
    realtime_price_ports = []
    for ticker in tickers:
        # Create a publisher for each ticker
        publisher_process, publisher_port = register_process_with_port(
                                                            target=realtime_price_publisher,
                                                            args=(ticker,),
                                                            need_port=True,
                                                            cpd=child_processes_data
                                                        )
        realtime_price_ports.append(publisher_port)
    
    # Create a manager process to aggregate prices
    prices_manager_process, prices_manager_port = register_process_with_port(
                                                            target=realtime_prices_manager,
                                                            args=(tickers, realtime_price_ports),
                                                            need_port=True,
                                                            cpd=child_processes_data
                                                        )
    
    # Create a consumer process to display prices
    prices_display_process, _ = register_process_with_port(
                                                            target=realtime_price_display_consumer,
                                                            args=(tickers, prices_manager_port),
                                                            need_port=False,
                                                            cpd=child_processes_data
                                                        )

    # Create trade execution processes for each ticker
    for ticker in tickers:
        trade_execution, _ = register_process_with_port(
                                                            target=individual_trade_execution,
                                                            args=(ticker, prices_manager_port),
                                                            need_port=False,
                                                            cpd=child_processes_data
                                                        )

    # Start all child processes
    child_processes = child_processes_data.child_processes
    try:
        # Start child processes
        for process in child_processes:
            process.start()

        # Keep the main process alive while child processes run
        while all([process.is_alive() for process in child_processes]):
            time.sleep(1)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Terminate processes if they are still running
        for process in child_processes:
            if process.is_alive():
                process.terminate()

        # Wait for processes to terminate
        for process in child_processes:
            process.join()

        print("Processes terminated.")
