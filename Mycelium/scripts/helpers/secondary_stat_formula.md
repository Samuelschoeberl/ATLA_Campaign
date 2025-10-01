# Secondary Stat Formulas

This file lists the secondary character stats and their formula expressions (sourced from `char_formulas.json`). It is formatted as a simple two-column markdown table for easy parsing.

## Format

- Parse the table rows under "## Secondary Stat Formulas".
- Each row is: | Stat Key | Formula |

## Secondary Stat Formulas

| Stat Key                      | Formula                                              |
| ----------------------------- | ---------------------------------------------------- |
| [[CL]]                        | CL                                                   |
| [[HP Multiplier]]             | 10                                                   |
| [[max_hit_points]]            | CON _ CL + Manually_Rolled_Hitpoints _ HP Multiplier |
| [[Player Root/Rules/Evasion]] | 10 + DEX + Airbending_Level                          |
| [[Armor definition]]          | 0 + Earthbending_Level                               |
| [[Stress Level]]              | 0                                                    |
| [[airbending_bonus]]          | Air Level + DEX                                      |
| [[airbending_dc]]             | 10 + airbending_bonus                                |
| [[waterbending_bonus]]        | Water Level + INT                                    |
| [[waterbending_dc]]           | 10 + waterbending_bonus                              |
| [[earthbending_bonus]]        | Earth Level + STR                                    |
| [[firebending_bonus]]         | Fire Level + WIS                                     |
| [[earthbending_dc]]           | 10 + earthbending_bonus                              |
| [[firebending_dc]]            | 10 + firebending_bonus                               |
| [[spiritbending_dc]]          | 10 + spiritbending                                   |
| [[spiritbending]]             | Spirit Level + WIS                                   |
| [[Waterbottle Charges]]       | Waterbottle Charges                                  |
| [[Air Level]]                 | Air                                                  |
| [[Airbending_Level]]          | Air                                                  |
| [[Water Level]]               | Water                                                |
| [[Waterbending_Level]]        | Water                                                |
| [[Earth Level]]               | Earth                                                |
| [[Earthbending_Level]]        | Earth                                                |
| [[Fire Level]]                | Fire                                                 |
| [[Firebending_Level]]         | Fire                                                 |
| [[Spirit Level]]              | Spirit                                               |
| [[Manually_Rolled_Hitpoints]] | Manually Rolled HP                                   |
| [[Manually Rolled HP]]        | Manually Rolled HP                                   |
| [[CON]]                       | CON                                                  |
| [[DEX]]                       | DEX                                                  |
| [[INT]]                       | INT                                                  |
| [[STR]]                       | STR                                                  |
| [[WIS]]                       | WIS                                                  |

<!-- End of file -->
#helpers #Mycelium #CL
