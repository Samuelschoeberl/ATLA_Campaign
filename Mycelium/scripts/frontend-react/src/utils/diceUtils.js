/**
 * Dice rolling utility functions
 */

/**
 * Roll dice expression (e.g., "2d6+3", "1d20+2+6")
 */
export function rollDiceExpression(expression) {
  // Parse dice expression with potentially multiple modifiers
  // Examples: 1d20, 2d6+3, 1d20+2+6, 3d6-1+2
  const basePattern = /^(\d+)d(\d+)/i;
  const match = expression.trim().match(basePattern);

  if (!match) {
    return {
      total: 0,
      numDice: 0,
      sides: 0,
      rolls: [],
      modifier: 0,
      error: "Invalid dice expression",
    };
  }

  const numDice = parseInt(match[1], 10);
  const sides = parseInt(match[2], 10);

  if (numDice < 1 || numDice > 99 || sides < 2 || sides > 1000) {
    return {
      total: 0,
      numDice: 0,
      sides: 0,
      rolls: [],
      modifier: 0,
      error: "Dice values out of range (1-99 dice, 2-1000 sides)",
    };
  }

  // Extract all modifiers (everything after the dice part)
  const remainingExpression = expression.trim().substring(match[0].length);

  // Parse all modifiers: +3, -2, +6, etc.
  let totalModifier = 0;
  const modifierMatches = remainingExpression.matchAll(/([+-]\d+)/g);
  for (const modMatch of modifierMatches) {
    totalModifier += parseInt(modMatch[1], 10);
  }

  const rolls = [];
  let sum = 0;
  for (let i = 0; i < numDice; i++) {
    const roll = Math.floor(Math.random() * sides) + 1;
    rolls.push(roll);
    sum += roll;
  }

  return {
    total: sum + totalModifier,
    numDice,
    sides,
    rolls,
    modifier: totalModifier,
  };
}
