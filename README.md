akka-log-highlighter
====================

Fork of the "colored logcat output" project (http://jsharkey.org/downloads/coloredlogcat.pytxt), which adds colors to logcat formatted output.

This version is different, in the sense that doesn't run any application, but instead reads from stdin and formats all lines matching a couple of regular expressions:
1) Akka log output format (actor systems, dispatchers, actors)
2) Some Java/Scala Stacktraces

###Installation
- First, make the script executable
`chmod +x hl.py`

- For convenience you can do something like:
`sudo mv hl.py /usr/bin/hl` or
`mv hl.py ~/bin/hl`

###Usage
- Run your app, pipe the output to the formatter
`your_akka_app | ./hl.py`

- You can also do this with logs, with either tail or cat.
`tail -f logfile | hl.py`
`cat logfile | hl.py`

###Adjustments
You can modify the column sizes hardcoded in the script to suit your needs. I acknowledge the code is not the very readable at all, but it serves its purpose well, and has a speed that is comparable to that of `tail`.
