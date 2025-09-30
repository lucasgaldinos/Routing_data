## Project Scope & Goals

1. **Primary output format**: Do you want both JSON and DuckDB outputs, or do you have a preference for one over the other?
   > Yes, both outputs are desired. The main thing is, the user should specify which one he wants. If he wants both, the system should generate both.

2. **Database purpose**: You mentioned wanting CRUD operations - what specific operations do you envision?
   - Just basic read/write/update of problem instances?
     > Yes, though the preference should be to update instead of recreating. The folder should be specified once (having `datasets/duckdb` as default) by the user and then the system should check if the file already exists, and if it does, update it.
   - Query capabilities for finding problems by characteristics (dimension, type, etc.)?
     > Yes, this is a must have. But any database can do this
   - Something more complex?
     > Yes, I want correct system workspace structure inside the `src` from the start. There's also a lot of design patterns that can be used to make the code more readable and maintainable from the get go.
     > - Possibility of refactoring the current tsplib95 (but only if to improve some calculations (e.g. using more modern libs or features, parallelization methods, vetorization, etc)). Identifying its good parts and reaplying its design for our development. You must use #deepwiki <https://deepwiki.com/rhgrant10/tsplib95> to find more information about.
     > - Tests and a simple documentation, focusing on diagrams and flowcharts, to make it easier for new developers to understand the code. Output it in [diagrams](./diagrams/).

## Data Structure & Schema

3. **Graph representation**: Should the database store:
   - Raw problem metadata only (name, type, dimension, etc.)?
     > No, all info about the problem. It's specially important to create a way to store the edge weights and node coordinates in a readable and connected way. The json can just be a dump of the all the objects created by the tsplib95 library.
   - Full node coordinates and edge weights?
      > Yes, for problems that offers only edge_weights, it should be parsed as
   - Pre-computed NetworkX graph structures?
      > No, but it should be possible to create a graph from the data stored. I think this is one of the slowest parts of the current tsplib95 library, so if we can improve it, it would be great.
   - All of the above?
     > No, read the blockquotes.

4. **File organization**: You have problems in `datasets_raw/problems/{tsp,vrp,atsp,hcp,sop,tour}/` - should the output maintain this categorization or flatten everything?
   > flatten everything, the problem type will be specified in the file.

## Performance & Scale

5. **Processing approach**: You mentioned parallel processing - what's your target performance? Are we talking about:
   - Processing hundreds of files quickly?
     > yes, but what are the tradeoffs? the files are pretty small. Most of them at least. And for now, we'll only be working with simpler problems. But be warned about other types of problems in the future.
   - Real-time conversion capabilities?
     > No, not yet
   - Batch processing that runs overnight?
     > No

6. **Memory constraints**: Should the system handle large problem instances (10k+ nodes) efficiently, or are we focusing on smaller benchmark problems?
   > Process everything, since data storage isn't the main point and calculations WON'T BE DONE IN THIS REPO. This repo's only job is ETL (Extract, Transform and Load) of the data. So, if it takes a bit longer to process a 10k nodes problem, it's ok.
  
## Integration & Usage

7. **API/Interface needs**: Besides CLI, do you need:
   - Python API for programmatic access?
     > A connection between duckdb and python should be made, so the user can access the database from python. But this is a feature of duckdb, not of this repo.
   - REST API for external tools?
      > No
   - Just file-based I/O?
     > Yes

8. **Existing tools integration**: Should this work with existing tsplib95 CLI commands, or replace them entirely?
   > No, tsplib95 is the backend, but this will also be changed systematically

Please clarify these points so I can create a proper implementation plan that actually meets your needs.

# Major points for all considerations

- Any improvement shall be applied one by one, with #get_user_input after ANY medium change (e.g. you'll parallelize or vectorize some function, you must ask me if I want to apply it or not, and answer any question I may have before proceeding).
- If anything isn't clear, ask me before proceeding.
- the `tsplib95 python library` is based entirely on [tsplib 95 specs](./../TSPLIB95.md). You must read it.
- For now, there's only problems from the the repository, all of them compliant to the tsplib95 parsing rules. The system should be built in a way that it can be extended to other types of problems in the future, but I'm just warning, we'll now focus on developing the database.
