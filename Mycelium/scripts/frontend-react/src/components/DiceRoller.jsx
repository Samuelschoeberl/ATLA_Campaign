import React, { useState } from "react";
import { rollDiceExpression } from "../utils/helpers";

const DiceRoller = ({ onLog }) => {
  const [customInput, setCustomInput] = useState("");
  const [diceQuantities, setDiceQuantities] = useState({
    d4: 1,
    d6: 1,
    d8: 1,
    d10: 1,
    d12: 1,
    d20: 1,
  });

  const diceTypes = ["d4", "d6", "d8", "d10", "d12", "d20"];

  const handleQuantityChange = (dice, value) => {
    const num = parseInt(value) || 1;
    setDiceQuantities((prev) => ({
      ...prev,
      [dice]: Math.max(1, Math.min(99, num)),
    }));
  };

  const handleRoll = (expression, diceType = null) => {
    const rollResult = rollDiceExpression(expression);

    if (rollResult.error) {
      onLog?.("error", "Dice Roll Error", rollResult.error);
    } else {
      const diceValues = rollResult.rolls.join("+");
      const modifierText =
        rollResult.modifier !== 0
          ? rollResult.modifier > 0
            ? ` + ${rollResult.modifier}`
            : ` - ${Math.abs(rollResult.modifier)}`
          : "";

      const rollsText = `[${rollResult.rolls.join(", ")}]`;

      onLog?.(
        "info",
        "Dice Roll",
        `${rollResult.numDice}d${rollResult.sides}(${diceValues})${modifierText} = ${rollResult.total}\nRolls: ${rollsText}`
      );

      // Reset quantity to 1 after rolling
      if (diceType) {
        setDiceQuantities((prev) => ({
          ...prev,
          [diceType]: 1,
        }));
      }
    }
  };

  const handleCustomRoll = () => {
    const expression = customInput.trim();
    if (!expression) {
      return;
    }
    handleRoll(expression);
    setCustomInput("");
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      handleCustomRoll();
    }
  };

  return (
    <div id="dice-roller">
      <h3>🎲 Dice Roller</h3>

      <div className="dice-buttons">
        {diceTypes.map((dice) => (
          <div key={dice} className="dice-btn-container">
            <input
              type="number"
              min="1"
              max="99"
              value={diceQuantities[dice]}
              onChange={(e) => handleQuantityChange(dice, e.target.value)}
              className="dice-quantity-input"
              onClick={(e) => e.stopPropagation()}
            />
            <button
              className="dice-btn"
              data-dice={dice}
              onClick={() => handleRoll(`${diceQuantities[dice]}${dice}`, dice)}
            >
              {dice.toUpperCase()}
            </button>
          </div>
        ))}
      </div>

      <div className="custom-roll">
        <input
          type="text"
          placeholder="2d6+3"
          value={customInput}
          onChange={(e) => setCustomInput(e.target.value)}
          onKeyPress={handleKeyPress}
        />
        <button onClick={handleCustomRoll}>Roll</button>
      </div>
    </div>
  );
};

export default DiceRoller;
