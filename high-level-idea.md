Alright, so here's the plan.

We want to make an annotation system for docs, that expects a folder called "src".

Within src there are extensions - we can think of them as maybe .py ? .cpp ? Let the user specify which extensions are valid.

There will be another folder called "metadata".

We may assume that : 

- the files in src are connected to each other somehow, i.e. form a coherent structure
- the metadata folder consists of PDFs which add context to the codebase.

There may be a special folder called "devin-skeleton" in the pwd as well.

So, 3 folders at the start - src, devin-skeleton, metadata.

Before you do anything, make a workable RAG-index using the metadata folder's PDFs.

Step 1 :

For each file, in parallel, set up runs using anthropic, to create precise, detailed notes. In the process, query the RAG index to see if it has anything to say.

- High quality notes prioritize the code file over the RAG.
- Aim to summarize such that you output 1 line of markdown for 10 lines of code.

At the end of this step, for each valid source file in src, there is a .md file, annotated accordingly.

Step 2 : 

Use tree-sitter and any other appropriate program analysis tools to form a "DAG" of the repository. That is, formulate a plan for an overall documentation in the form of a markdown file, which starts by :

- Having all the per-file notes - you have this from step 1 
- Use program analysis to decide how files link to each other, and what should be done next.
- Step by step, execute this plan, to create intermediate .md files that cover all the linkages.

Step 3 : 

Near the end, we should have :

per file notes in a folder
intermediate steps in another
a folder called "high-level overview" which should be populated from step 2 - this covers the repo - i.e. the src folder - at the highest possible level, and is used to form the table of contents for the overall output.

If the devin folder was present, add the PDFs from the devin folder into the high-level overview.

Using the API, upload all of this to Gemini.

Decide : 

- How many parts and lines we should ask for. Each "part" should be 1500 words tops, and you should tell Gemini to first output a table of contents, and then, one by one, output the parts linked to each section mentioned in the table of contents.

Every time gemini outputs a part, you save it as a .md file, and ask for the next part.

This continues till all the parts are done.

You should always ask Gemini to do it in the tone of a dry engineering manual, cut fluff, and be technical and rigorous. You should ask it to cut filler words such that each section can be output directly to a .md.

At the end of the run, you should end up with some .md files for the table of contents and per section. 