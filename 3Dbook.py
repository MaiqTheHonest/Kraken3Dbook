import asyncio
import websockets
import json
import numpy as np
import matplotlib.pyplot as plt
import bisect
from matplotlib.ticker import FormatStrFormatter
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import time

#%matplotlib auto

### to deal with runtimeerror:
import nest_asyncio
nest_asyncio.apply()
###

# settables
book_depth: int = 25
ticker: str = "ETH/USD"
runtime: int = 10

_zbCu = []
_zaCu = []
bbars = []
abars = []
time_passed = 0
temp_list1 = []
temp_list2 = []
temp_list3 = []


# initialize bar plot
fig = plt.figure(figsize=(20, 10), tight_layout=True)
gs = gridspec.GridSpec(4, 5, width_ratios=[1,1,1,1,1], top=0.92, bottom=0.08, hspace=1, wspace = 0.1, right=0.98)
ax1 = fig.add_subplot(gs[:,2:], projection='3d')
ax1.view_init(elev = 9, azim=-95)
ax1.yaxis.set_rotate_label(False)
ax1.zaxis.set_rotate_label(False)
ax1.set_xlabel("bid / ask price", labelpad=40)
ax1.set_ylabel("epochs", labelpad=20, rotation=94)
ax1.set_zlabel("aggregated volume", labelpad=30, rotation=90)
ax1.xaxis.set_major_formatter(FormatStrFormatter('%.2f'))
ax1.tick_params(axis='y', pad=10)
ax1.tick_params(axis='z', pad=10)
ax1.set_title(f"{ticker} order book, aggregated volume", y=0.93)
green_patch = mpatches.Patch(color=[0.094, 0.349, 0.141], label='bids')
red_patch = mpatches.Patch(color=[0.984, 0.247, 0.090], label='asks')
plt.legend(handles=[green_patch, red_patch], title=f"\n book depth = {book_depth} \n", loc=[0.9, 0.005])

# initialize midmarket line plot
ax2 = fig.add_subplot(gs[:2,:2])
ax2.set_xlabel("epochs", labelpad=10)
ax2.set_ylabel("mid-price", labelpad=10)
ax2.xaxis.set_label_coords(1.08, 0.01)
ax2.set_title(f"{ticker} midmarket", pad=20)
ax2.grid(True)

# initialize skew line plot
ax3 = fig.add_subplot(gs[2:,:2])
ax3.spines['right'].set_color('none')
ax3.spines['top'].set_color('none')
ax3.xaxis.set_ticks_position('bottom')
ax3.yaxis.set_ticks_position('left')
ax3.spines['bottom'].set_position('center')
ax3.set_xlabel("epochs", labelpad=25)
ax3.xaxis.set_label_coords(1.08, 0.51)
ax3.set_ylabel("skew", labelpad=10)
ax3.set_title(f"{ticker} skew", pad=20)
ax3.grid(True)


plt.ion()



def order_unpack(order_data):
    
    if isinstance(order_data, list) is True:
                    
        if 'a' in order_data[1]:
            order_type = 'ask'
            if len(order_data[1]['a']) < 2:
                uni_order = order_data[1]['a'][0][:2]
                clearing_price = None
            else:
                uni_order = order_data[1]['a'][1][:2]
                clearing_price = float(order_data[1]['a'][0][0])
        elif 'b' in order_data[1]:
            order_type = 'bid'
            if len(order_data[1]['b']) < 2:
                uni_order = order_data[1]['b'][0][:2]
                clearing_price = None
            else:
                uni_order = order_data[1]['b'][1][:2]
                clearing_price = float(order_data[1]['b'][0][0])            
        else:
            return None
        
        return uni_order, order_type, clearing_price



async def kraken_ws():
    url = "wss://ws.kraken.com/"
    try:
        async with websockets.connect(url, ping_interval=None) as websocket:
            subscribe_msg = {
                "event": "subscribe",
                "pair": [ticker],
                "subscription": {"name": "book",
                                 "depth": book_depth}
            }

            await websocket.send(json.dumps(subscribe_msg))

            # Run the loop for (runtime) seconds
            end_time = asyncio.get_event_loop().time() + runtime  
            
            linecount = 0
            headers = []
            
            # store the first 3 lines for later
            while linecount < 3:
                response = await websocket.recv()
                data = json.loads(response)
                print(data)

                if 'heartbeat' not in str(data):
                    headers.append(data)
                    linecount += 1

            header1, header2, snapshot = headers 

            asklist = snapshot[1]["as"]
            bidlist = snapshot[1]["bs"]

            _xa = [float(ask[0]) for ask in asklist]
            _za = [float(ask[1]) for ask in asklist]
            _xb = [float(bid[0]) for bid in bidlist]
            _zb = [float(bid[1]) for bid in bidlist]
            _xb.reverse()
            _zb.reverse()
            
            global _zbCu # important these globals are declared here and not elsewhere
            global _zaCu
            
            ### REPETITION
            def update_cycle(uni_order, order, clearing_price):

                if clearing_price is not None:
                    clearing_price = float('%.10g' % clearing_price)  # removes trailing zeroes
                nonlocal _za, _zb, _xa, _xb
                global _zbCu, _zaCu
                _zbCu = _zbCu
                _zaCu = _zaCu

                if uni_order is not None:
                    inc_price = float(uni_order[0])
                    inc_volume = float(uni_order[1])



                if order == 'bid':
                    tpos = bisect.bisect_left(_xb, inc_price)

                    if inc_price not in _xb:
                        removed_pos = 0
                    else:
                        removed_pos = tpos + 1
                    
                    bisect.insort(_xb, inc_price)
                    _zb.insert(tpos, inc_volume)

                    if clearing_price == None or clearing_price not in _xb:
                        _xb.pop(removed_pos)
                        _zb.pop(removed_pos)
                    else:
                        index = _xb.index(clearing_price)
                        _xb.pop(index)
                        _zb.pop(index) 

                    _zbCu = []
                    for count, value in enumerate(list(reversed(_zb))):
                        if count == 0:
                            _zbCu.append(value)
                        else:
                            _zbCu.append(value + _zbCu[count-1])

                    _zbCu.reverse()


                    
                elif order == 'ask':
                    cpos = bisect.bisect_left(_xa, inc_price)

                    if inc_price not in _xa:
                        removed_pos = -1
                    else:
                        removed_pos = cpos + 1

                    bisect.insort(_xa, inc_price)
                    _za.insert(cpos, inc_volume)
                    
                    if clearing_price == None or clearing_price not in _xa:
                        _xa.pop(removed_pos)
                        _za.pop(removed_pos)
                    else:
                        index = _xa.index(clearing_price)
                        _xa.pop(index)
                        _za.pop(index)

                    _zaCu = []
                    for count, value in enumerate(_za):
                        if count == 0:
                            _zaCu.append(value)
                        else:
                            _zaCu.append(value + _zaCu[count-1])



                # setting the correct bar widths for plotting
                _plotxa = []
                _plotxb = []

                _rxb = list(reversed(_xb))

                for count, value in enumerate(_rxb):

                    if count != len(_rxb) - 1:
                        _plotxb.append(_rxb[count+1] - value)
                    else:
                        _plotxb.append(0)
                _plotxb.reverse()


                for count, value in enumerate(_xa):
                    if count != len(_xa) - 1:
                        _plotxa.append(_xa[count+1] - value)
                    else:
                        _plotxa.append(0.01)

                return _xa, _za, _xb, _zb, _zbCu, _zaCu, _plotxa, _plotxb



            # for the first snapshot, we pass empty order data
            # but still need to do the cumulative order calc.
            _xa, _za, _xb, _zb, _zbCu, _zaCu, _plotxa, _plotxb = update_cycle(None, None, None)
    
            _zbCu = []
            for count, value in enumerate(list(reversed(_zb))):
                if count == 0:
                    _zbCu.append(value)
                else:
                    _zbCu.append(value + _zbCu[count-1])

            _zbCu.reverse()


            _zaCu = []
            for count, value in enumerate(_za):
                if count == 0:
                    _zaCu.append(value)
                else:
                    _zaCu.append(value + _zaCu[count-1])

                


            def update_graph(_xa, _za, _xb, _zb, _zbCu, _zaCu, _plotxa, _plotxb):  # drawing bars, then changing ticks
                start = time.time()
                global time_passed, midmarket, skew, ticklabels
                midmarket = (_xb[-1] + _xa[0])/2
                skew = _zaCu[-1] - _zbCu[0]
                time_passed -= 1
                depth = 1
                bottomB = np.zeros_like(_zbCu)
                bottomA = np.zeros_like(_zaCu)

                bbar = ax1.bar3d(_xb, time_passed, bottomB, _plotxb, depth, _zbCu, color=[0.223, 0.835, 0.341], shade=True)
                abar = ax1.bar3d(_xa, time_passed, bottomA, _plotxa, depth, _zaCu, color=[0.984, 0.247, 0.090], shade=True)


                bbars.append(bbar)
                abars.append(abar)

                if time_passed < -5:
                    temp_bar1 = bbars[time_passed*(-1)-6]
                    temp_bar2 = abars[time_passed*(-1)-6]
                    temp_bar1.remove()
                    temp_bar2.remove()
                    # del also has to be called to clear the bars from memory
                    del temp_bar1
                    del temp_bar2

                
                ticks = list(np.arange(_xb[0]-0.1, _xa[-1]+0.1, 0.5)) + [midmarket]
                ax1.set_xticks(ticks)
                ticks.pop(-1)

                ticklabels = ax1.get_xticklabels()
                


                ticklabels[-1].set_fontsize(0)
                ax1.set_ylim(time_passed, time_passed+5)
                ax1.set_xlim(min(_xb)*0.9999, max(_xa)*1.0001) ##################################################
                ax1.tick_params(axis='x', rotation=280)

                temp_list1.append(time_passed*(-1))
                temp_list2.append(midmarket)
                line1 = ax2.plot(temp_list1, temp_list2, c=[0.501, 0.376, 0.965])
                ax2.get_yaxis().get_major_formatter().set_useOffset(False)

                temp_list3.append(skew)
                line2 = ax3.plot(temp_list1, temp_list3, c=[0.501, 0.376, 0.965])
                res = [abs(ele) for ele in temp_list3]
                ax3.set_ylim(-max(res)*1.01, max(res)*1.01)
                plt.draw()
                plt.pause(0.01)
                #ax1.set_xticks(ticks=ticks, rotation=90)
                line1.pop(0).remove()
                line2.pop(0).remove()
                ticklabels[-1].set_fontsize(10)
                
                end = time.time()
                print(f"{(end-start)*10**3:.03f}ms")




            # process the rest of the lines (the live feed)
            while True:

                response = await websocket.recv()
                data = json.loads(response)
                print(type(data), data)
                otp = order_unpack(data)
                
                if otp is not None:
                    clicker = update_cycle(otp[0], otp[1], otp[2])
                    update_graph(*clicker)

                # Stop the loop at reaching end_time
                if asyncio.get_event_loop().time() >= end_time:
                    plt.ioff()
                    plt.close()
                    print("Loop finished")
                    break

    except asyncio.CancelledError:
        print("WebSocket connection closed")

    

# Run the asyncio loop for a limited time
async def main():
    await kraken_ws()

asyncio.get_event_loop().run_until_complete(main())  # the actual asyncio call

