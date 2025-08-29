import { RefreshCw } from "lucide-react";
import { useState } from "react";

export default function ResetChatButton() {
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipOpacity, setTooltipOpacity] = useState(0);
  let tooltipTimeout = null;
  
  const handleMouseEnter = (e) => {
    // Clear any existing timeout
    if (tooltipTimeout) clearTimeout(tooltipTimeout);
    
    // Show tooltip after 200ms (0.2s) to match GitHub Home tooltip timing
    tooltipTimeout = setTimeout(() => {
      setShowTooltip(true);
      // Use small delay to allow DOM update before starting the opacity transition
      setTimeout(() => {
        setTooltipOpacity(1);
      }, 10);
      e.currentTarget.style.backgroundColor = "rgba(255, 255, 255, 0.1)";
    }, 200);
  };
  
  const handleMouseLeave = (e) => {
    // Clear the timeout if user moves away before tooltip shows
    if (tooltipTimeout) clearTimeout(tooltipTimeout);
    setTooltipOpacity(0);
    // Short delay before hiding to allow fade out animation
    setTimeout(() => {
      setShowTooltip(false);
    }, 150);
    e.currentTarget.style.backgroundColor = "transparent";
  };
  
  const handleResetChat = async () => {
    // First call the reset_chat action to clear the Langgraph thread
    await callAction({ name: "reset_chat", payload: {} });
    
    // Then reload the page to clear the UI
    window.location.reload();
  };
  
  return (
    <div style={{ 
      position: "fixed", 
      top: "14px",  // Fine-tuned to align with the Readme button
      left: "80px", // Position it to the left
      zIndex: 1000 
    }}>
      {/* Custom tooltip - styled to match GitHub Home tooltip */}
      {showTooltip && (
        <div style={{
          position: "absolute",
          top: "100%",
          left: "0",
          backgroundColor: "#424242",
          color: "#fff",
          padding: "6px 12px",
          borderRadius: "6px",
          marginTop: "8px",
          fontSize: "14px",
          fontWeight: "normal",
          whiteSpace: "nowrap",
          boxShadow: "0 1px 3px rgba(0, 0, 0, 0.4)",
          zIndex: 1001,
          fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
          opacity: tooltipOpacity,
          transform: tooltipOpacity ? "translateY(0)" : "translateY(-3px)",
          transition: "opacity 0.15s ease-out, transform 0.15s ease-out"
        }}>
          This action resets your chat
        </div>
      )}
      
      <div
        onClick={handleResetChat}
        className="cl-navbar-item"
        style={{ 
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: "6px",
          fontSize: "14px", 
          fontWeight: "500", 
          padding: "8px 12px", // Increased vertical padding
          height: "40px", // Increased height to match Readme button
          color: "var(--cl-white, #fff)",
          borderRadius: "10px",
          border: "2px solid #ff3333", // Bright red border
          transition: "background-color 0.2s ease",
          boxSizing: "border-box", // Ensures padding is included in height calculation
          position: "relative" // For tooltip positioning
        }}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <RefreshCw size={18} style={{ marginBottom: "1px" }} /> {/* Using a refresh icon with adjusted size */}
        Reset Chat
      </div>
    </div>
  );
}
