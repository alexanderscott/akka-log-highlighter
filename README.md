akka-log-highlighter
====================

Highlighter for Akka output. It reads from stdin and formats whatever matches a regular expression that describes the default Akka logging output format.

Usage:
- Makes the script executable
```chmod +x hl.py```

```your_program | ./hl.py```

- For convenience you can do something like:
```sudo mv hl.py /usr/bin/some_name```

```your_program | some_name```
