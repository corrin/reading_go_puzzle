# Important

New design change.
Rather than guess the next move, I want to change it to 'guess the value of sente'.

For example.  You hold the black stones on this board.  What's the score difference between moving and you passing?

Also the app "Go: The Infinite Path" showed that integrating an engine is essential.  
Rather than just preprocessing with Katrain, I want to include it on the website.  So the user is asked "yo, how many points for a pass?"
The user answers 10.  The app then uses the engine to say: "m'kay, and why is taking ten points better than here?".  The user clicks a reply to that move, and the engine calculates the adjusted score

I.e. 
1. How does the value of pass compare to the true value of pass calculated by the engine.  Then 
2. is the value of pass entered by the user equal or higher than the score difference from impact of the two move sequence

For a phased approach we could have just the first one.  Grab random games off the internet.  Run the engine offline.  Save the value of pass at each move.
Then we can have a 'guess the value of pass' game. 

Then we add the 'prove it' as Phase 2.

Note this will require a rename of the app since it's no longer Tsumego.  Reading Go Puzzle still works.