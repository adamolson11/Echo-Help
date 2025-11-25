import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import Intake from "./Intake";
import Search from "./Search";

function App() {
  const [count, setCount] = useState(0)
  const [tab, setTab] = useState<'search' | 'intake'>('search');

  return (
    <>
      <div>
        <a href="https://vite.dev" target="_blank">
          <img src={viteLogo} className="logo" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank">
          <img src={reactLogo} className="logo react" alt="React logo" />
        </a>
      </div>
      <h1>Vite + React</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
        <p>
          Edit <code>src/App.tsx</code> and save to test HMR
        </p>
      </div>
      <p className="read-the-docs">
        Click on the Vite and React logos to learn more
      </p>
      <div style={{ margin: '1rem 0' }}>
        <button onClick={() => setTab('search')}>Search</button>
        <button onClick={() => setTab('intake')}>Intake</button>
      </div>
      {tab === 'intake' ? <Intake /> : <Search />}
    </>
  )
}

export default App
