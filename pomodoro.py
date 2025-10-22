#!/usr/bin/env python3
"""
Pomodoro Timer - Manage your study sessions
"""

import argparse
import subprocess
import os
from datetime import datetime

class Pomodoro:
    def __init__(self, work_mins=25, short_break=5, long_break=15, cycles=4):
        self.work_mins = work_mins
        self.short_break = short_break
        self.long_break = long_break
        self.cycles = cycles
        self.log_file = os.path.expanduser("~/.pomodoro_log")
    
    def notify(self, title, message, urgency="normal"):
        """Send desktop notification"""
        subprocess.run(['notify-send', '-u', urgency, title, message])
    
    def play_sound(self):
        """Play system sound"""
        try:
            subprocess.run(['paplay', '/usr/share/sounds/freedesktop/stereo/complete.oga'], 
                         stderr=subprocess.DEVNULL)
        except:
            print('\a')  # Fallback beep
    
    def log_session(self, session_type, duration):
        """Log completed sessions"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.log_file, 'a') as f:
            f.write(f"{timestamp} | {session_type} | {duration} min\n")
    
    def countdown(self, minutes, label):
        """Run termdown countdown"""
        print(f"\n{'='*50}")
        print(f"  {label}")
        print(f"{'='*50}\n")
        
        # Run termdown - just let it run, don't check return code
        subprocess.run(['termdown', f'{minutes}m'])
    
    def run(self):
        """Run the full pomodoro session"""
        print("\n🍅 POMODORO SESSION STARTING")
        print(f"📋 Plan: {self.cycles} cycles of {self.work_mins} min work")
        print(f"☕ Breaks: {self.short_break} min short, {self.long_break} min long\n")
        
        input("Press ENTER to begin...")
        
        for cycle in range(1, self.cycles + 1):
            # Work session
            self.notify("Pomodoro Started", 
                       f"Cycle {cycle}/{self.cycles} - Focus time!", 
                       "critical")
            
            self.countdown(self.work_mins, f"🍅 FOCUS TIME - Cycle {cycle}/{self.cycles}")
            
            self.play_sound()
            self.log_session(f"Work-{cycle}", self.work_mins)
            
            print("\n✅ Work session complete!")
            
            # Break decision
            if cycle == self.cycles:
                # Long break after all cycles
                print("\n✅ ALL CYCLES COMPLETE!")
                self.notify("Session Complete!", 
                           f"Amazing work! Take a {self.long_break} min break", 
                           "critical")
                
                self.countdown(self.long_break, "☕ LONG BREAK - You earned it!")
                self.play_sound()
                self.log_session("Long Break", self.long_break)
                break
            else:
                # Short break between cycles
                self.notify("Break Time!", 
                           f"Rest for {self.short_break} minutes", 
                           "normal")
                
                self.countdown(self.short_break, f"☕ SHORT BREAK - {self.cycles - cycle} cycles left")
                
                self.play_sound()
                self.log_session("Short Break", self.short_break)
                
                print("\n⏰ Break's over! Get ready for the next round...")
                input("Press ENTER to continue...")
        
        print("\n" + "="*50)
        print("  🎉 POMODORO SESSION COMPLETE! 🎉")
        print("="*50)
        print(f"\n✅ Completed {self.cycles} focus sessions")
        print(f"⏱️  Total focus time: {self.work_mins * self.cycles} minutes\n")
        
        self.notify("Pomodoro Complete!", 
                   "Excellent work today!", 
                   "critical")

def show_stats():
    """Show pomodoro statistics"""
    log_file = os.path.expanduser("~/.pomodoro_log")
    
    if not os.path.exists(log_file):
        print("No pomodoro sessions logged yet!")
        return
    
    with open(log_file, 'r') as f:
        lines = f.readlines()
    
    if not lines:
        print("No pomodoro sessions logged yet!")
        return
    
    today = datetime.now().strftime("%Y-%m-%d")
    today_sessions = [l for l in lines if l.startswith(today)]
    
    print("\n📊 POMODORO STATISTICS")
    print("="*50)
    print(f"Total sessions all-time: {len(lines)}")
    print(f"Sessions today: {len(today_sessions)}")
    
    # Calculate today's focus time
    today_work = [l for l in today_sessions if "Work-" in l]
    if today_work:
        total_mins = sum(int(l.split('|')[2].strip().split()[0]) for l in today_work)
        print(f"Focus time today: {total_mins} minutes ({total_mins/60:.1f} hours)")
    
    print(f"\n📝 Last 5 sessions:")
    for line in lines[-5:]:
        print(f"  {line.strip()}")
    print()

def main():
    parser = argparse.ArgumentParser(
        description='🍅 Pomodoro Timer - Manage your study sessions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pomo                    # Standard: 4x25min work, 5min breaks
  pomo -w 50 -s 10        # Custom: 50min work, 10min breaks
  pomo -c 2               # Just 2 cycles
  pomo --stats            # View your statistics
        """
    )
    
    parser.add_argument('-w', '--work', type=int, default=25,
                       help='Work session length in minutes (default: 25)')
    parser.add_argument('-s', '--short', type=int, default=5,
                       help='Short break length in minutes (default: 5)')
    parser.add_argument('-l', '--long', type=int, default=15,
                       help='Long break length in minutes (default: 15)')
    parser.add_argument('-c', '--cycles', type=int, default=4,
                       help='Number of work cycles (default: 4)')
    parser.add_argument('--stats', action='store_true',
                       help='Show pomodoro statistics')
    
    args = parser.parse_args()
    
    if args.stats:
        show_stats()
        return
    
    # Check if termdown is installed
    try:
        subprocess.run(['which', 'termdown'], 
                      check=True, 
                      stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("❌ Error: termdown not found!")
        print("Install with: pip install termdown")
        return
    
    pomo = Pomodoro(
        work_mins=args.work,
        short_break=args.short,
        long_break=args.long,
        cycles=args.cycles
    )
    
    try:
        pomo.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Pomodoro interrupted!")
        print("Don't give up - try again when ready! 💪\n")

if __name__ == "__main__":
    main()
