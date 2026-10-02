import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Activity, Navigation, Battery, Signal, Radio, 
  Crosshair, LayoutGrid, RotateCcw, RotateCw, 
  ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Square,
  ShieldAlert, ShieldCheck, Play,
  MousePointer2, Keyboard, Map as MapIcon, History,
  Maximize
} from 'lucide-react';
import './App.css'; 

const createDroneIcon = (isSelected, heading) => {
  return L.divIcon({
    className: 'custom-drone-icon',
    html: `
      <div style="
        width: 36px; 
        height: 36px; 
        background: ${isSelected ? 'rgba(59, 130, 246, 0.4)' : 'rgba(255, 255, 255, 0.1)'};
        border: 2px solid ${isSelected ? '#60a5fa' : 'rgba(255,255,255,0.3)'};
        border-radius: 50%;
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        display: flex;
        align-items: center;
        justify-content: center;
        transform: rotate(${heading}deg);
        box-shadow: 0 0 15px ${isSelected ? 'rgba(59, 130, 246, 0.6)' : 'rgba(0,0,0,0.5)'};
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      ">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="${isSelected ? '#ffffff' : '#e2e8f0'}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
          <polygon points="12 2 15 7 9 7 12 2" fill="${isSelected ? '#60a5fa' : 'transparent'}"/>
        </svg>
      </div>
    `,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
};

const initialDrones = Array.from({ length: 6 }, (_, i) => ({
  id: i + 1,
  lat: 37.7749 + (Math.random() - 0.5) * 0.015,
  lng: -122.4194 + (Math.random() - 0.5) * 0.015,
  alt: 50 + Math.random() * 50,
  heading: Math.random() * 360,
  battery: 70 + Math.random() * 30,
  gps: true,
  connected: true,
  mode: 'LOITER',
  trail: []
}));

export default function App() {
  const [drones, setDrones] = useState(initialDrones);
  const [selectedDrones, setSelectedDrones] = useState([1, 2]);
  const [logs, setLogs] = useState(["[SYSTEM] Glassmorphism GCS Initialized.", "[INFO] Awaiting telemetry..."]);
  
  const centerPadRef = useRef(null);

  const addLog = (msg) => {
    setLogs(prev => {
      const newLogs = [`[${new Date().toLocaleTimeString()}] ${msg}`, ...prev];
      return newLogs.slice(0, 100); 
    });
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.repeat) return; // Prevent spam
      const key = e.key.toUpperCase();
      const validKeys = ['W', 'A', 'S', 'D', 'Q', 'E', ' ', 'R'];
      if (validKeys.includes(key) && e.target.tagName !== 'INPUT') {
        e.preventDefault();
        let action = '';
        switch(key) {
          case 'W': action = 'PITCH FORWARD'; break;
          case 'S': action = 'PITCH BACKWARD'; break;
          case 'A': action = 'ROLL LEFT'; break;
          case 'D': action = 'ROLL RIGHT'; break;
          case 'Q': action = 'YAW LEFT'; break;
          case 'E': action = 'YAW RIGHT'; break;
          case ' ': action = 'THROTTLE UP'; break;
          case 'R': action = 'THROTTLE DOWN'; break;
          default: break;
        }
        addLog(`[KEYBOARD] ${key} -> ${action}`);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setDrones(prev => prev.map(d => {
        const dLat = (Math.random() - 0.5) * 0.0002;
        const dLng = (Math.random() - 0.5) * 0.0002;
        const newLat = d.lat + dLat;
        const newLng = d.lng + dLng;
        const newTrail = [...d.trail, [newLat, newLng]].slice(-30); 
        return {
          ...d,
          lat: newLat,
          lng: newLng,
          heading: (d.heading + (Math.random() - 0.5) * 20) % 360,
          battery: Math.max(0, d.battery - 0.05),
          trail: newTrail
        };
      }));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const toggleDrone = (id) => {
    setSelectedDrones(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const selectAll = () => setSelectedDrones(drones.map(d => d.id));
  const deselectAll = () => setSelectedDrones([]);

  const handleAction = (action) => {
    if (selectedDrones.length === 0) {
      addLog("[WARN] No drones selected for action: " + action);
      return;
    }
    addLog(`[COMMAND] ${action} on Drones: ${selectedDrones.join(', ')}`);
  };

  const handleMouseControl = (e) => {
    if (!centerPadRef.current) return;
    const rect = centerPadRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left - rect.width/2;
    const y = e.clientY - rect.top - rect.height/2;
    const nx = (x / (rect.width/2)).toFixed(2);
    const ny = (y / (rect.height/2)).toFixed(2);
    if(e.buttons === 1) {
      addLog(`[MOUSE FLIGHT] Pitch: ${-ny}, Roll: ${nx}`);
    }
  };

  return (
    <div className="dashboard-container">
      {/* 1. TOP BAR */}
      <div className="panel top-panel glass-panel glow-border">
        <div className="brand flex-row">
          <div className="logo-pulse">
            <Radio size={24} color="#60a5fa"/>
          </div>
          <h1 className="title-glow">AETHER SWARM CMD</h1>
        </div>
        
        <div className="top-stats flex-row" style={{ gap: 32 }}>
          <div className="stat flex-row">
            <Signal size={18} color="var(--success)"/>
            <span>Uplink: <strong style={{color:'var(--success)'}}>100%</strong></span>
          </div>
          <div className="stat flex-row">
            <Activity size={18} color="var(--accent-primary)"/>
            <span>Active: <strong>{drones.length}</strong></span>
          </div>
          <div className="stat flex-row">
            <Battery size={18} color="var(--warning)"/>
            <span>Avg Bat: <strong>{(drones.reduce((a,b)=>a+b.battery,0)/drones.length).toFixed(0)}%</strong></span>
          </div>
        </div>

        <div className="top-actions flex-row" style={{ gap: 16 }}>
          <button className="btn btn-danger glass-btn" onClick={() => handleAction('ARM ALL')}>
            <ShieldAlert size={16}/> ARM
          </button>
          <button className="btn glass-btn" onClick={() => handleAction('DISARM ALL')}>
            <ShieldCheck size={16}/> DISARM
          </button>
          <div className="divider-v" />
          <button className="btn btn-success glass-btn" onClick={() => handleAction('TAKEOFF')}>
            <ArrowUp size={16}/> TAKEOFF
          </button>
          <button className="btn glass-btn" onClick={() => handleAction('LAND')}>
            <ArrowDown size={16}/> LAND
          </button>
        </div>
      </div>

      {/* 2. LEFT PANEL */}
      <div className="panel left-panel glass-panel flex-col glow-border">
        <div className="panel-header glass-header">
          <MapIcon size={18} color="var(--accent-primary)"/> Mission Planner
        </div>
        <div className="panel-content flex-col scrollable" style={{ gap: 20 }}>
          <div className="glass-card">
            <h4 className="card-title">Active Mission</h4>
            <div className="progress-container">
              <div className="progress-bar-glow" style={{width:'65%'}}></div>
            </div>
            <div className="flex-row space-between text-small mt-2" style={{color:'var(--text-muted)'}}>
              <span>Waypoint 8 / 12</span>
              <span>ETA 04:12</span>
            </div>
          </div>

          <div className="glass-card">
            <h5 className="card-title mb-2">Pattern Generation</h5>
            <div className="grid-2">
              <button className="btn glass-btn-small" onClick={() => addLog('Grid Plan Requested')}><LayoutGrid size={14}/> Grid</button>
              <button className="btn glass-btn-small" onClick={() => addLog('Spiral Plan Requested')}><RotateCw size={14}/> Spiral</button>
              <button className="btn glass-btn-small" onClick={() => addLog('Perimeter Plan Requested')}><Square size={14}/> Border</button>
              <button className="btn glass-btn-small" onClick={() => addLog('Scan Plan Requested')}><Activity size={14}/> Scan</button>
            </div>
          </div>

          <div className="glass-card flex-1">
            <h5 className="card-title mb-2"><History size={16}/> Execution History</h5>
            <div className="history-list">
              {logs.filter(l => l.includes('COMMAND') || l.includes('Plan')).slice(0,8).map((l, i) => (
                <div key={i} className="history-item text-small">
                  <span style={{color:'var(--accent-primary)'}}>{l.split(']')[0]}]</span> 
                  {l.split(']')[1]}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 3. CENTER PANEL */}
      <div className="center-area flex-col">
        <div className="map-container-wrapper glow-border">
          <MapContainer 
            center={[37.7749, -122.4194]} 
            zoom={16} 
            zoomControl={false}
            style={{ width: '100%', height: '100%', background: '#050505', zIndex: 1 }}
          >
            <TileLayer
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            />
            {drones.map(d => (
              <React.Fragment key={d.id}>
                <Marker 
                  position={[d.lat, d.lng]} 
                  icon={createDroneIcon(selectedDrones.includes(d.id), d.heading)}
                >
                  <Popup className="glass-popup">
                    <div className="popup-content">
                      <strong>Drone {d.id}</strong>
                      <div>Alt: {d.alt.toFixed(1)}m</div>
                      <div>Bat: {d.battery.toFixed(0)}%</div>
                      <div>Hdg: {d.heading.toFixed(0)}&deg;</div>
                    </div>
                  </Popup>
                </Marker>
                {d.trail.length > 1 && (
                  <Polyline 
                    positions={d.trail} 
                    color={selectedDrones.includes(d.id) ? "#60a5fa" : "rgba(255,255,255,0.2)"} 
                    weight={selectedDrones.includes(d.id) ? 3 : 1} 
                    opacity={0.8} 
                    dashArray={selectedDrones.includes(d.id) ? "0" : "4"} 
                  />
                )}
              </React.Fragment>
            ))}
          </MapContainer>

          {/* Mouse Flight Controller Overlay */}
          <div className="flight-controller-overlay glass-panel">
             <div className="overlay-header glass-header-small">
               <MousePointer2 size={12}/> VIRTUAL JOYSTICK
             </div>
             <div 
               className="control-pad" 
               ref={centerPadRef}
               onMouseMove={handleMouseControl}
               onMouseDown={handleMouseControl}
             >
               <div className="crosshair-v"></div>
               <div className="crosshair-h"></div>
               <div className="center-dot"></div>
               <span className="label top">W</span>
               <span className="label bottom">S</span>
               <span className="label left">A</span>
               <span className="label right">D</span>
             </div>
          </div>
        </div>
      </div>

      {/* 4. RIGHT PANEL */}
      <div className="panel right-panel glass-panel flex-col glow-border">
        <div className="panel-header glass-header">
          <Maximize size={18} color="var(--accent-primary)"/> Telemetry Matrix
        </div>
        <div className="panel-content flex-col scrollable">
          <div className="grid-2 mb-2">
            <button className="btn glass-btn" onClick={selectAll}>Select All</button>
            <button className="btn glass-btn" onClick={deselectAll}>Clear</button>
          </div>
          
          <div className="drone-list flex-col">
            {drones.map(d => {
              const isSel = selectedDrones.includes(d.id);
              return (
                <div 
                  key={d.id} 
                  className={`drone-card glass-card ${isSel ? 'selected' : ''}`}
                  onClick={() => toggleDrone(d.id)}
                >
                  <div className="flex-row space-between mb-2">
                    <strong className="text-glow">Node 0{d.id}</strong>
                    <span className="badge online-pulse">ACTV</span>
                  </div>
                  <div className="grid-2 text-small">
                    <div className="flex-row"><Battery size={14} color={d.battery > 30 ? '#10b981' : '#ef4444'}/> {d.battery.toFixed(1)}%</div>
                    <div className="flex-row"><Navigation size={14} color="#60a5fa"/> {d.heading.toFixed(0)}&deg;</div>
                    <div className="flex-row"><MapIcon size={14}/> {d.alt.toFixed(1)}m</div>
                    <div className="flex-row"><Activity size={14}/> {d.mode}</div>
                  </div>
                  {isSel && (
                     <div className="mini-graph mt-2 flex-row" style={{alignItems:'flex-end', height: 24, gap: 2}}>
                        {Array.from({length: 12}).map((_, i) => (
                           <div key={i} className="bar-anim" style={{
                             height: `${20 + Math.random()*80}%`, 
                             width: '100%',
                             background: 'linear-gradient(to top, #3b82f6, #93c5fd)',
                             borderRadius: 2,
                             opacity: 0.8
                           }}></div>
                        ))}
                     </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* 5. BOTTOM PANEL */}
      <div className="panel bottom-panel glass-panel flex-row glow-border" style={{ gap: 16 }}>
        <div className="flex-col" style={{ flex: 2 }}>
          <div className="panel-header glass-header-small" style={{borderBottom:'none'}}>
            <Keyboard size={16} color="var(--accent-primary)"/> System Terminal (WASD Q E Space R)
          </div>
          <div className="panel-content console-content scrollable" style={{ padding: '0 16px 16px 16px' }}>
            {logs.map((l, i) => {
              let color = '#e2e8f0';
              if (l.includes('WARN')) color = '#f59e0b';
              if (l.includes('KEYBOARD') || l.includes('MOUSE')) color = '#a78bfa';
              if (l.includes('COMMAND')) color = '#60a5fa';
              
              return (
                <div key={i} className="log-line" style={{color}}>
                  <span className="log-prefix" style={{opacity:0.5}}>{'>'}</span> {l}
                </div>
              );
            })}
          </div>
        </div>
        
        <div className="divider-v" style={{ height: 'auto', alignSelf: 'stretch', margin: '16px 0' }}></div>

        <div className="flex-col" style={{ flex: 1, padding: 16 }}>
          <div className="glass-header-small mb-2" style={{borderBottom:'none'}}>
            <Activity size={16} color="var(--success)"/> Packet Statistics
          </div>
          <div className="grid-2 text-small">
            <div className="glass-card" style={{padding: 10}}>
               <div style={{color:'var(--text-muted)'}}>Tx Rate</div>
               <div style={{fontSize:'1.2rem', color:'var(--success)', fontWeight:'bold'}}>1.2 <span style={{fontSize:'0.7rem'}}>MB/s</span></div>
            </div>
            <div className="glass-card" style={{padding: 10}}>
               <div style={{color:'var(--text-muted)'}}>Rx Rate</div>
               <div style={{fontSize:'1.2rem', color:'var(--accent-primary)', fontWeight:'bold'}}>3.4 <span style={{fontSize:'0.7rem'}}>MB/s</span></div>
            </div>
            <div className="glass-card" style={{padding: 10}}>
               <div style={{color:'var(--text-muted)'}}>Packet Loss</div>
               <div style={{fontSize:'1.2rem', color:'var(--warning)', fontWeight:'bold'}}>0.02 <span style={{fontSize:'0.7rem'}}>%</span></div>
            </div>
            <div className="glass-card" style={{padding: 10}}>
               <div style={{color:'var(--text-muted)'}}>Latency</div>
               <div style={{fontSize:'1.2rem', color:'#a78bfa', fontWeight:'bold'}}>14 <span style={{fontSize:'0.7rem'}}>ms</span></div>
            </div>
          </div>
          <div className="mt-2 text-small" style={{color:'var(--text-muted)'}}>CPU Performance (Avg)</div>
          <div className="progress-container mt-2">
            <div className="progress-bar-glow" style={{width: `${40 + Math.random()*20}%`, background: '#a78bfa'}}></div>
          </div>
        </div>
      </div>
    </div>
  );
}
