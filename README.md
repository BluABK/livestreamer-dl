# livestreamer-dl

Livestreamer Download is a stripped down port of [acccentor/livestreamertest](https://github.com/acccentor/livestreamertest) which merely downloads a stream on-demand.
It has none of the nifty automation and API integration, and is primarily intended to work as a more usable frontend for "livestreamer -o ...".

Available commands:
```
dl [channel] [title]                 Download a stream (no args gives interactive prompt)
list                                 Lists current active downloads
history                              Lists all active and inactive downloads (and their status)
stop [ID]                            Ends a stream (NB: Currently out of order)
kill [ID]                            Kills a stream (NB: Currently out of order)
quit                                 Closes streams and quits the program (NB: Unable to close streams)
help                                 Take a guess..

Example:
>: dl northernlion Northern Lion Super Show (Josh day) - The Binding of Isaac

Developer features:
gimme2                               Download a stream using livestreamer module instead of shellex
```
