import React, { useState } from "react";
import { rollDiceExpression } from "../utils/diceUtils";
import "./DiceRoller.css";

const DiceRoller = ({ lightMode = false }) => {
  const [customInput, setCustomInput] = useState("");
  const [diceQuantities, setDiceQuantities] = useState({
    d4: 1,
    d6: 1,
    d8: 1,
    d10: 1,
    d12: 1,
    d20: 1,
  });
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [rollHistory, setRollHistory] = useState([]);

  const diceTypes = ["d4", "d6", "d8", "d10", "d12", "d20"];

  const handleQuantityChange = (dice, value) => {
    const num = parseInt(value) || 1;
    setDiceQuantities((prev) => ({
      ...prev,
      [dice]: Math.max(1, Math.min(99, num)),
    }));
  };

  const addToHistory = (rollInfo) => {
    const timestamp = new Date().toLocaleTimeString();
    setRollHistory((prev) => [
      {
        ...rollInfo,
        timestamp,
        id: Date.now() + Math.random(),
      },
      ...prev.slice(0, 19), // Keep last 20 rolls
    ]);
  };

  const handleRoll = (expression, diceType = null) => {
    const rollResult = rollDiceExpression(expression);

    if (rollResult.error) {
      addToHistory({
        expression,
        error: rollResult.error,
        isError: true,
      });
    } else {
      const modifierText =
        rollResult.modifier !== 0
          ? rollResult.modifier > 0
            ? ` + ${rollResult.modifier}`
            : ` - ${Math.abs(rollResult.modifier)}`
          : "";

      addToHistory({
        expression,
        numDice: rollResult.numDice,
        sides: rollResult.sides,
        rolls: rollResult.rolls,
        modifier: rollResult.modifier,
        modifierText,
        total: rollResult.total,
        isError: false,
      });

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

  const clearHistory = () => {
    setRollHistory([]);
  };

  return (
    <div className={`dice-roller-container ${isCollapsed ? 'collapsed' : ''} ${lightMode ? 'light-mode' : ''}`}>
      <div className="dice-roller-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <h3>
          <span className="dice-icon">🎲</span>
          Dice Roller
        </h3>
        <button 
          className="collapse-btn"
          onClick={(e) => {
            e.stopPropagation();
            setIsCollapsed(!isCollapsed);
          }}
          aria-label={isCollapsed ? "Expand" : "Collapse"}
        >
          {isCollapsed ? '▼' : '▲'}
        </button>
      </div>

      {!isCollapsed && (
        <>
          <div className="dice-roller-content">
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

          <div className="roll-output">
            <div className="roll-output-header">
              <h4>Roll History</h4>
              {rollHistory.length > 0 && (
                <button className="clear-history-btn" onClick={clearHistory}>
                  Clear
                </button>
              )}
            </div>
            <div className="roll-history">
              {rollHistory.length === 0 ? (
                <div className="no-rolls">No rolls yet. Roll some dice!</div>
              ) : (
                rollHistory.map((roll) => (
                  <div 
                    key={roll.id} 
                    className={`roll-entry ${roll.isError ? 'error' : ''}`}
                  >
                    <div className="roll-time">{roll.timestamp}</div>
                    {roll.isError ? (
                      <div className="roll-error">
                        <strong>{roll.expression}</strong>: {roll.error}
                      </div>
                    ) : (
                      <div className="roll-result">
                        <div className="roll-expression">
                          {roll.numDice}d{roll.sides}{roll.modifierText}
                        </div>
                        <div className="roll-details">
                          Rolls: [{roll.rolls.join(", ")}]
                        </div>
                        <div className="roll-total">
                          Total: <strong>{roll.total}</strong>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default DiceRoller;
