import React, { useState, useEffect } from 'react';
import { escapeHtml } from '../utils/helpers';

const EventLog = ({ events, onClearEvent }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getSeverityIcon = (severity) => {
    if (severity === 'error') {
      return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" fill="#FDE8EA"/>
          <path d="M12 7v6" stroke="#D45A6B" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M12 16h.01" stroke="#D45A6B" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      );
    }
    if (severity === 'warn') {
      return (
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" fill="#FFF3E6"/>
          <path d="M12 8v5" stroke="#D99A3A" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M12 15h.01" stroke="#D99A3A" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      );
    }
    return (
      <svg viewBox="0 0 24 24" width="18" height="18" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" fill="#E8F4FF"/>
        <path d="M8 12h8" stroke="#4A86D6" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    );
  };

  const lastTwoEvents = events.slice(-2).reverse();

  return (
    <div id="event-log" className={isExpanded ? 'expanded' : ''}>
      {!isExpanded ? (
        <div className="log-header">
          <div className="compact">
            {lastTwoEvents.map((event, idx) => (
              <div key={idx} className="compact-text">
                {event.title}: {event.text.split('\n')[0]}
              </div>
            ))}
          </div>
          <button onClick={() => setIsExpanded(true)}>Expand</button>
        </div>
      ) : (
        <>
          <div className="log-header">
            <strong>Event Log</strong>
            <button onClick={() => setIsExpanded(false)}>Minimize</button>
          </div>
          <div className="log-body" id="event-log-body">
            {events.map((event, idx) => (
              <div key={idx} className={`event-entry ${event.severity}`}>
                <div className="ts">{event.timestamp}</div>
                <div style={{ display: 'flex', alignItems: 'center' }}>
                  <span style={{ display: 'inline-block', width: '18px', height: '18px', marginRight: '8px' }}>
                    {getSeverityIcon(event.severity)}
                  </span>
                  <strong>{event.title}</strong>
                </div>
                <div style={{ marginTop: '6px' }}>
                  {event.text.split('\n').map((line, i) => (
                    <React.Fragment key={i}>
                      {line}
                      {i < event.text.split('\n').length - 1 && <br />}
                    </React.Fragment>
                  ))}
                </div>
                <div className="event-actions">
                  <button onClick={() => onClearEvent(idx)}>Close</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default EventLog;
