# Kool-AI-Chess
![image](https://github.com/DelroyGayle/KoolAIChess/assets/91061592/cedf65e7-23b2-47a6-beb1-e0b2dc097035)



**Kool AI Chess - A command line Chess program using Python - Player vs Computer**

## Introduction

This is **Version 2** of my command line Chess program *Kool AI*, that I wrote whilst studying for a Diploma with Code Institute.
For full details and instructions please refer to this [README](README_FOR_VERSION1.md).

**Version 1** is slow! Sometimes, it takes over 20 seconds for *Kool AI* to respond with its move! Therefore, the goal of **Version 2** is to speed up the running of this program.

Since **Version 1** was my very first Python program, in my naivety, there are indeed various places where I can see the reasons for the lethargy.
Predominantly, I had not used any *List Comprehensions*. Instead, I had used simple For Loops to process lists of 'Chess Moves'.

However, *'List Comprehensions can be faster than For Loops* because they are optimised for performance by Python's internal mechanisms.

Therefore, using List Comprehensions would be the first step in increasing the speed of *Kool AI*.

------

## Future Features
* Attempt to speed up the program by using a library such as [itertools](https://docs.python.org/3/library/itertools.html)
* The ability to switch sides
* Undo/Redo ability when playing moves
* Saving board positions during the game
* Loading of saved positions
* Explore further the possibilities of **Chess-Playing Automation** using the existing functionality
* Loading and playing of [PGN](https://en.wikipedia.org/wiki/Portable_Game_Notation) chess files
* A Colour Chessboard using a library such as [Colorama](https://pypi.org/project/colorama/)
* Better Graphics for the Chess Pieces and the Chessboard

------

## Testing

+ Passed the code through the PEP8 linter and confirmed there are no problems.
+ Carried out tests of the program on both the local terminal and the Code Institute Heroku terminal.
+ Added functionality so that this program could read Chess moves from a [PGN](https://en.wikipedia.org/wiki/Portable_Game_Notation) file, namely, *input.pgn*.<br>
My rationale is that if my program can play *recorded chess games **identically*** then the chess-playing algorithm works correctly.<br>
See [TESTING.md](https://github.com/DelroyGayle/KoolAIChess/blob/main/TESTING.md) for further details.

### Internal Errors

At the top level of the program I have added the following *try-except* :- 

```
def main():
    try:
        main_part2()
    except CustomException as error:
        print(error)
        handle_internal_error()
        quit()
    except Exception as error:
        raise error
```

That way, if there is some *logic error that I have not anticipated or some internal error occurs*;<br>
it would be caught here and a suitable message would be printed.

The message will be of the form:<br>

<strong>Internal Error: \<The Error Message\><br>
Computer resigns due to an internal error<br>
Please investigate<br>
<br>
Thank You For Playing<br>
Goodbye<br>
</strong>

------

## Credits
Please refer to [README](README_FOR_VERSION1.md).
        
## Acknowledgements    
Please refer to [README](README_FOR_VERSION1.md).
