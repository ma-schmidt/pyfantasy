pyfantasy
=========

An unofficial API to view and modify Yahoo Fantasy data. This wrapper comes with no garantee of any sort.


Installation
------------

As with most python packages, the easiest method to install is by using pip:

.. code-block:: bash

    $ pip install pyfantasy


Usage
-----

The first step is to create a FantasyAPI object. 

.. code-block:: python

	>>> fapi = FantasyAPI('cred.json')

This will do many things. First, it will log you into yahoo's two step autentication process. Second, it will give you access to the `get' method to retrieve any available data. Third, it will automatically store basic data related to the fantasy teams owned by the credentials passed.

You can then use this information to modify or view a particular team

.. code-block:: python

	>>> team_info = fapi.teams[0]
	>>> my_team = fapi.get_team(team_info.team_key)
	>>> for player in my_team.players:
	...     print(player)
	...
	<Player: C    - Ryan Kesler (C)>
	<Player: C    - Evgeni Malkin (C)>
	<Player: LW   - Jakub Voracek (LW,RW)>
	<Player: LW   - Max Pacioretty (LW)>
	<Player: RW   - Nikolaj Ehlers (LW,RW)>
	<Player: RW   - Patrick Kane (RW)>
	<Player: D    - Kevin Shattenkirk (D)>
	<Player: D    - Alex Pietrangelo (D)>
	<Player: D    - Torey Krug (D)>
	<Player: D    - Erik Johnson (D)>
	<Player: Util - Rickard Rakell (C,LW)>
	<Player: BN   - Zdeno Chara (D)>
	<Player: G    - Roberto Luongo (G)>
	<Player: G    - John Gibson (G)>
	<Player: BN   - Jonathan Bernier (G)>

The most advanced feature of this package is certainly the possibility to compute the "optimal" lineup assignment. Using a maximum weighted matching algorithm, the method `start_active' creates the optimal assignment between your players and the available positions. It prioritizes healthy players that are playing on that day. Furthermore, it uses the average draft pick of a player to order between them if some players need to be benched.

Unfortunately, the documentation is currently extremelly sparse and below any reasonable standards. Sorry.