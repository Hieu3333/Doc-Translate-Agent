1. Implement true agent (agent continuously call tools until it completes the task)
Right only implement the 2-turn agent (plan tool+execute -> summarize)

Add feature: show the implementation steps in a box and show the overall response after that


2. When translating batch of flatten list of texts like this and paste them back exactly where they are, the final content on the result file may not be good due to the difference in languages' grammar.
For example: English: S V O
             Japanese: S O V
---> Add the texts back exactly may break the meaning of the sentence. 

Maybe this issue is not critical, just to keep in mind