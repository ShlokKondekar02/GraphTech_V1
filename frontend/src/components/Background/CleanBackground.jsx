import React, { useEffect, useState } from 'react';
import bgImage from '../../assets/bg-clean.png';

export function CleanBackground() {
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  useEffect(() => {
    let frameId;
    let targetX = 0;
    let targetY = 0;
    let currentX = 0;
    let currentY = 0;

    const handleMouseMove = (e) => {
      const { innerWidth, innerHeight } = window;
      // Gentle normalized offset from center: -1 to +1
      const normX = (e.clientX - innerWidth / 2) / (innerWidth / 2);
      const normY = (e.clientY - innerHeight / 2) / (innerHeight / 2);
      // Subtle shift: max 8px
      targetX = normX * 8;
      targetY = normY * 6;
    };

    const animate = () => {
      // Smooth lerp
      currentX += (targetX - currentX) * 0.05;
      currentY += (targetY - currentY) * 0.05;
      setOffset({ x: currentX, y: currentY });
      frameId = requestAnimationFrame(animate);
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    frameId = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(frameId);
    };
  }, []);

  return (
    <div className="clean-background-container" aria-hidden="true">
      {/* Pristine Clean Perspective Image with subtle responsive parallax */}
      <div 
        className="clean-background-image"
        style={{
          backgroundImage: `url(${bgImage})`,
          transform: `translate3d(${-offset.x}px, ${-offset.y}px, 0) scale(1.04)`
        }}
      />
      {/* Subtle lighting wash for clean readability and contrast */}
      <div className="clean-background-overlay" />
    </div>
  );
}

export default CleanBackground;
