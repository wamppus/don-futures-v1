#!/usr/bin/env python3
"""
DON Futures v1 — Trading GUI

Features:
- Real-time price display
- Strategy status & position tracking
- Live trade log
- Session P&L tracking
- Start/Stop controls
- Settings panel

Usage:
    python gui.py
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from datetime import datetime
import threading
import queue
import json

sys.path.insert(0, os.path.dirname(__file__))

from bot import (
    DonFuturesStrategy, DonFuturesConfig, VALIDATED_CONFIG,
    create_data_feed, get_logger
)


class DonFuturesGUI:
    """
    Main GUI for DON Futures v1 Strategy
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("DON Futures v1 — Failed Test Strategy")
        self.root.geometry("1200x800")
        self.root.configure(bg='#1a1a2e')
        
        # State
        self.running = False
        self.strategy = None
        self.data_feed = None
        self.message_queue = queue.Queue()
        
        # Session stats
        self.session_trades = 0
        self.session_wins = 0
        self.session_losses = 0
        self.session_pnl = 0.0
        
        # Current data
        self.current_price = 0.0
        self.current_bid = 0.0
        self.current_ask = 0.0
        self.channel_high = 0.0
        self.channel_low = 0.0
        
        # Build UI
        self._build_ui()
        
        # Start message processor
        self._process_messages()
        
        self.log("GUI initialized. Configure settings and click START.")
    
    def _build_ui(self):
        """Build the main UI"""
        
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main container
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        
        # === TOP ROW: Status & Price ===
        top_frame = ttk.Frame(main)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Status indicator
        self.status_frame = tk.Frame(top_frame, bg='#2d2d44', padx=20, pady=10)
        self.status_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_label = tk.Label(
            self.status_frame, text="⏹ STOPPED", 
            font=('Helvetica', 16, 'bold'), fg='#ff6b6b', bg='#2d2d44'
        )
        self.status_label.pack()
        
        # Price display
        price_frame = tk.Frame(top_frame, bg='#2d2d44', padx=20, pady=10)
        price_frame.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        self.price_label = tk.Label(
            price_frame, text="0.00", 
            font=('Helvetica', 32, 'bold'), fg='#4ecdc4', bg='#2d2d44'
        )
        self.price_label.pack()
        
        self.bid_ask_label = tk.Label(
            price_frame, text="Bid: 0.00 | Ask: 0.00",
            font=('Helvetica', 10), fg='#888', bg='#2d2d44'
        )
        self.bid_ask_label.pack()
        
        # Channel display
        channel_frame = tk.Frame(top_frame, bg='#2d2d44', padx=20, pady=10)
        channel_frame.pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(channel_frame, text="CHANNEL", font=('Helvetica', 10), 
                 fg='#888', bg='#2d2d44').pack()
        self.channel_label = tk.Label(
            channel_frame, text="H: 0.00\nL: 0.00",
            font=('Helvetica', 14, 'bold'), fg='#f9ca24', bg='#2d2d44'
        )
        self.channel_label.pack()
        
        # Session P&L
        pnl_frame = tk.Frame(top_frame, bg='#2d2d44', padx=20, pady=10)
        pnl_frame.pack(side=tk.RIGHT)
        
        tk.Label(pnl_frame, text="SESSION P&L", font=('Helvetica', 10),
                 fg='#888', bg='#2d2d44').pack()
        self.pnl_label = tk.Label(
            pnl_frame, text="$0.00",
            font=('Helvetica', 24, 'bold'), fg='#4ecdc4', bg='#2d2d44'
        )
        self.pnl_label.pack()
        self.stats_label = tk.Label(
            pnl_frame, text="0W / 0L (0%)",
            font=('Helvetica', 10), fg='#888', bg='#2d2d44'
        )
        self.stats_label.pack()
        
        # === MIDDLE: Position & Log ===
        middle = ttk.Frame(main)
        middle.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Left: Position panel
        left_frame = ttk.LabelFrame(middle, text="Position", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 10))
        
        self.position_text = tk.Text(
            left_frame, width=30, height=10, 
            bg='#2d2d44', fg='white', font=('Courier', 11),
            state=tk.DISABLED
        )
        self.position_text.pack(fill=tk.BOTH, expand=True)
        self._update_position_display()
        
        # Right: Trade log
        right_frame = ttk.LabelFrame(middle, text="Trade Log", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(
            right_frame, height=15, 
            bg='#1a1a2e', fg='#4ecdc4', font=('Courier', 10),
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure log tags
        self.log_text.tag_configure('entry', foreground='#4ecdc4')
        self.log_text.tag_configure('exit_win', foreground='#6bff6b')
        self.log_text.tag_configure('exit_loss', foreground='#ff6b6b')
        self.log_text.tag_configure('info', foreground='#888')
        self.log_text.tag_configure('warning', foreground='#f9ca24')
        
        # === BOTTOM: Controls & Settings ===
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X, pady=(10, 0))
        
        # Controls
        controls = ttk.Frame(bottom)
        controls.pack(side=tk.LEFT)
        
        self.start_btn = ttk.Button(
            controls, text="▶ START", command=self._start,
            style='Accent.TButton'
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            controls, text="⏹ STOP", command=self._stop,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            controls, text="Clear Log", command=self._clear_log
        ).pack(side=tk.LEFT, padx=5)
        
        # Settings
        settings = ttk.LabelFrame(bottom, text="Settings", padding=5)
        settings.pack(side=tk.RIGHT)
        
        # Symbol
        ttk.Label(settings, text="Symbol:").pack(side=tk.LEFT, padx=2)
        self.symbol_var = tk.StringVar(value="ES")
        symbol_combo = ttk.Combobox(
            settings, textvariable=self.symbol_var,
            values=["ES", "MES"], width=5, state='readonly'
        )
        symbol_combo.pack(side=tk.LEFT, padx=2)
        
        # Interval
        ttk.Label(settings, text="Interval:").pack(side=tk.LEFT, padx=(10, 2))
        self.interval_var = tk.StringVar(value="5")
        interval_combo = ttk.Combobox(
            settings, textvariable=self.interval_var,
            values=["1", "5", "15"], width=3, state='readonly'
        )
        interval_combo.pack(side=tk.LEFT, padx=2)
        ttk.Label(settings, text="min").pack(side=tk.LEFT)
        
        # Mode
        ttk.Label(settings, text="Mode:").pack(side=tk.LEFT, padx=(10, 2))
        self.mode_var = tk.StringVar(value="Shadow")
        mode_combo = ttk.Combobox(
            settings, textvariable=self.mode_var,
            values=["Shadow", "Live"], width=8, state='readonly'
        )
        mode_combo.pack(side=tk.LEFT, padx=2)
    
    def _process_messages(self):
        """Process messages from background threads"""
        try:
            while True:
                msg = self.message_queue.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass
        
        self.root.after(100, self._process_messages)
    
    def _handle_message(self, msg):
        """Handle a message from the strategy"""
        msg_type = msg.get('type')
        
        if msg_type == 'log':
            self.log(msg['text'], msg.get('tag', 'info'))
        
        elif msg_type == 'price':
            self.current_price = msg['price']
            self.current_bid = msg.get('bid', 0)
            self.current_ask = msg.get('ask', 0)
            self._update_price_display()
        
        elif msg_type == 'channel':
            self.channel_high = msg['high']
            self.channel_low = msg['low']
            self._update_channel_display()
        
        elif msg_type == 'position':
            self._update_position_display(msg)
        
        elif msg_type == 'entry':
            self.log(
                f"🟢 ENTRY: {msg['direction'].upper()} @ {msg['price']:.2f} "
                f"[{msg['entry_type']}]",
                'entry'
            )
            self._update_position_display(msg)
        
        elif msg_type == 'exit':
            pnl = msg['pnl_pts']
            self.session_trades += 1
            self.session_pnl += pnl * 50  # ES point value
            
            if pnl > 0:
                self.session_wins += 1
                tag = 'exit_win'
                emoji = '✅'
            else:
                self.session_losses += 1
                tag = 'exit_loss'
                emoji = '❌'
            
            self.log(
                f"{emoji} EXIT: {pnl:+.2f} pts (${pnl*50:+,.0f}) — {msg['reason']}",
                tag
            )
            self._update_pnl_display()
            self._update_position_display({'in_position': False})
    
    def _update_price_display(self):
        """Update price labels"""
        self.price_label.config(text=f"{self.current_price:.2f}")
        self.bid_ask_label.config(
            text=f"Bid: {self.current_bid:.2f} | Ask: {self.current_ask:.2f}"
        )
    
    def _update_channel_display(self):
        """Update channel labels"""
        self.channel_label.config(
            text=f"H: {self.channel_high:.2f}\nL: {self.channel_low:.2f}"
        )
    
    def _update_pnl_display(self):
        """Update P&L labels"""
        color = '#6bff6b' if self.session_pnl >= 0 else '#ff6b6b'
        self.pnl_label.config(text=f"${self.session_pnl:+,.0f}", fg=color)
        
        if self.session_trades > 0:
            wr = self.session_wins / self.session_trades * 100
            self.stats_label.config(
                text=f"{self.session_wins}W / {self.session_losses}L ({wr:.0f}%)"
            )
    
    def _update_position_display(self, pos=None):
        """Update position panel"""
        self.position_text.config(state=tk.NORMAL)
        self.position_text.delete(1.0, tk.END)
        
        if pos and pos.get('in_position'):
            text = f"""
POSITION ACTIVE

Direction:  {pos.get('direction', '').upper()}
Entry Type: {pos.get('entry_type', '')}
Entry:      {pos.get('entry_price', 0):.2f}
Stop:       {pos.get('stop', 0):.2f}
Target:     {pos.get('target', 0):.2f}

Trail Stop: {pos.get('trail_stop', 'Not active')}
"""
        else:
            text = """
NO POSITION

Waiting for signal...

Strategy: Failed Test
- Fade liquidity sweeps
- 85% win rate validated
"""
        
        self.position_text.insert(tk.END, text)
        self.position_text.config(state=tk.DISABLED)
    
    def log(self, text, tag='info'):
        """Add message to log"""
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {text}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _clear_log(self):
        """Clear the log"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _start(self):
        """Start the strategy"""
        if self.running:
            return
        
        self.running = True
        self.status_label.config(text="▶ RUNNING", fg='#6bff6b')
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        mode = self.mode_var.get()
        symbol = self.symbol_var.get()
        interval = int(self.interval_var.get())
        
        self.log(f"Starting {mode} mode: {symbol} @ {interval}min", 'info')
        
        if mode == "Live":
            self.log("⚠️  LIVE MODE — REAL ORDERS WILL BE PLACED", 'warning')
        else:
            self.log("📝 Shadow mode — paper trading only", 'info')
        
        # Start in background thread
        self.strategy_thread = threading.Thread(
            target=self._run_strategy,
            args=(symbol, interval, mode),
            daemon=True
        )
        self.strategy_thread.start()
    
    def _stop(self):
        """Stop the strategy"""
        if not self.running:
            return
        
        self.running = False
        self.status_label.config(text="⏹ STOPPED", fg='#ff6b6b')
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        if self.data_feed:
            self.data_feed.stop()
        
        self.log("Strategy stopped.", 'info')
    
    def _run_strategy(self, symbol, interval, mode):
        """Run strategy in background thread"""
        try:
            # Initialize strategy
            config = VALIDATED_CONFIG
            if symbol == "MES":
                config = DonFuturesConfig(
                    **{**VALIDATED_CONFIG.__dict__, 'point_value': 5.0}
                )
            
            self.strategy = DonFuturesStrategy(config, "logs")
            
            # Initialize data feed
            self.data_feed = create_data_feed({
                'symbol': symbol,
                'bar_interval': interval
            })
            
            # Set up callbacks
            def on_bar(bar):
                if not self.running:
                    return
                
                # Update price
                self.message_queue.put({
                    'type': 'price',
                    'price': bar.close,
                    'bid': bar.low,
                    'ask': bar.high
                })
                
                # Process through strategy
                signal = self.strategy.add_bar(bar.to_dict(), bar.source)
                
                # Update channel
                if len(self.strategy.bars) >= 10:
                    ch_high = max(b['high'] for b in self.strategy.bars[-11:-1])
                    ch_low = min(b['low'] for b in self.strategy.bars[-11:-1])
                    self.message_queue.put({
                        'type': 'channel',
                        'high': ch_high,
                        'low': ch_low
                    })
                
                if signal:
                    if signal['action'] == 'entry':
                        self.message_queue.put({
                            'type': 'entry',
                            'in_position': True,
                            **signal
                        })
                    elif signal['action'] == 'exit':
                        self.message_queue.put({
                            'type': 'exit',
                            **signal
                        })
            
            self.data_feed.on_bar(on_bar)
            
            # Load historical data for warmup
            self.message_queue.put({'type': 'log', 'text': 'Loading historical data...'})
            bars = self.data_feed.fetch_historical(50)
            for bar in bars:
                self.strategy.add_bar(bar.to_dict(), 'historical')
            
            self.message_queue.put({
                'type': 'log', 
                'text': f'Warmup complete: {len(bars)} bars loaded'
            })
            
            # Start live feed
            self.message_queue.put({'type': 'log', 'text': 'Starting live data feed...'})
            self.data_feed.start()
            
            # Keep thread alive
            while self.running:
                import time
                time.sleep(0.5)
            
        except Exception as e:
            self.message_queue.put({
                'type': 'log',
                'text': f'Error: {e}',
                'tag': 'warning'
            })
            self.running = False


def main():
    root = tk.Tk()
    
    # Set dark theme colors
    root.tk_setPalette(
        background='#1a1a2e',
        foreground='white',
        activeBackground='#2d2d44',
        activeForeground='white'
    )
    
    app = DonFuturesGUI(root)
    
    # Handle window close
    def on_close():
        if app.running:
            app._stop()
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == '__main__':
    main()
