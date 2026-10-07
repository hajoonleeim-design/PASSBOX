import { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Bloom, EffectComposer } from '@react-three/postprocessing'
import * as THREE from 'three'

// PASSBOX mascot "Passbot", built procedurally: a shield-shaped hood, a dark glossy
// visor with glowing cyan eyes, and a small teardrop body with a glowing keyhole.
// It floats, blinks, and turns its head toward the pointer.
const CYAN = '#22d3ee'

function shieldShape(scale = 1, dy = 0) {
  const s = new THREE.Shape()
  const p = (x: number, y: number) => [x * scale, y * scale + dy] as const
  s.moveTo(...p(-0.85, 0.6))
  s.bezierCurveTo(...p(-0.85, 0.95), ...p(-0.5, 1.05), ...p(0, 1.05))
  s.bezierCurveTo(...p(0.5, 1.05), ...p(0.85, 0.95), ...p(0.85, 0.6))
  s.bezierCurveTo(...p(0.85, -0.2), ...p(0.45, -0.7), ...p(0, -0.95))
  s.bezierCurveTo(...p(-0.45, -0.7), ...p(-0.85, -0.2), ...p(-0.85, 0.6))
  return s
}

function keyholeShape() {
  const s = new THREE.Shape()
  s.absarc(0, 0.06, 0.1, 0, Math.PI * 2, false)
  const k = new THREE.Shape()
  k.moveTo(-0.05, 0)
  k.lineTo(-0.085, -0.2)
  k.lineTo(0.085, -0.2)
  k.lineTo(0.05, 0)
  k.closePath()
  return [s, k]
}

function Sparkles() {
  const ref = useRef<THREE.Points>(null)
  const { positions, seeds } = useMemo(() => {
    const count = 70
    const positions = new Float32Array(count * 3)
    const seeds = Array.from({ length: count }, (_, i) => ({
      r: 1.5 + ((i * 37) % 100) / 100 * 1.1,
      a: (i / count) * Math.PI * 2 * 3.7,
      y: -1.8 + ((i * 53) % 100) / 100 * 3.6,
      s: 0.15 + ((i * 17) % 10) / 60,
    }))
    return { positions, seeds }
  }, [])

  useFrame((state) => {
    const pts = ref.current
    if (!pts) return
    const t = state.clock.elapsedTime
    const attr = pts.geometry.attributes.position as THREE.BufferAttribute
    seeds.forEach((sd, i) => {
      const a = sd.a + t * sd.s
      attr.setXYZ(i, Math.cos(a) * sd.r, sd.y + Math.sin(t * sd.s * 2 + i) * 0.25, Math.sin(a) * sd.r * 0.6)
    })
    attr.needsUpdate = true
  })

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial color={CYAN} size={0.06} sizeAttenuation transparent opacity={0.9} depthWrite={false} toneMapped={false} />
    </points>
  )
}

function Bot() {
  const root = useRef<THREE.Group>(null)
  const head = useRef<THREE.Group>(null)
  const eyes = useRef<THREE.Group>(null)
  const armL = useRef<THREE.Mesh>(null)
  const armR = useRef<THREE.Mesh>(null)

  const headGeo = useMemo(
    () => new THREE.ExtrudeGeometry(shieldShape(1), { depth: 0.45, bevelEnabled: true, bevelSegments: 10, bevelSize: 0.1, bevelThickness: 0.12, curveSegments: 40 }),
    [],
  )
  const visorGeo = useMemo(
    () => new THREE.ExtrudeGeometry(shieldShape(0.78, 0.06), { depth: 0.03, bevelEnabled: true, bevelSegments: 6, bevelSize: 0.03, bevelThickness: 0.02, curveSegments: 40 }),
    [],
  )
  const keyholeGeo = useMemo(() => new THREE.ExtrudeGeometry(keyholeShape(), { depth: 0.02, bevelEnabled: false }), [])

  useFrame((state) => {
    const t = state.clock.elapsedTime
    const { x, y } = state.pointer
    if (root.current) {
      root.current.position.y = Math.sin(t * 1.4) * 0.12
      root.current.rotation.z = Math.sin(t * 0.9) * 0.035
    }
    if (head.current) {
      head.current.rotation.y += (x * 0.55 - head.current.rotation.y) * 0.08
      head.current.rotation.x += (-y * 0.3 - head.current.rotation.x) * 0.08
    }
    if (eyes.current) {
      const blink = Math.sin(t * 0.8 + 1) > 0.985 ? 0.08 : 1
      eyes.current.scale.y += (blink - eyes.current.scale.y) * 0.5
    }
    if (armL.current) armL.current.rotation.z = 0.5 + Math.sin(t * 2) * 0.12
    if (armR.current) armR.current.rotation.z = -0.5 - Math.sin(t * 2 + 1) * 0.12
  })

  return (
    <group ref={root} position={[0, -0.1, 0]}>
      {/* body */}
      <mesh position={[0, -1.35, 0]} scale={[0.72, 0.8, 0.6]}>
        <sphereGeometry args={[1, 64, 48]} />
        <meshPhysicalMaterial color="#eaf6fb" roughness={0.28} clearcoat={1} clearcoatRoughness={0.15} emissive={CYAN} emissiveIntensity={0.18} />
      </mesh>
      <mesh ref={armL} position={[-0.78, -1.15, 0.05]} scale={[0.18, 0.4, 0.18]} rotation={[0, 0, 0.5]}>
        <sphereGeometry args={[1, 32, 24]} />
        <meshPhysicalMaterial color="#eaf6fb" roughness={0.3} clearcoat={1} emissive={CYAN} emissiveIntensity={0.16} />
      </mesh>
      <mesh ref={armR} position={[0.78, -1.15, 0.05]} scale={[0.18, 0.4, 0.18]} rotation={[0, 0, -0.5]}>
        <sphereGeometry args={[1, 32, 24]} />
        <meshPhysicalMaterial color="#eaf6fb" roughness={0.3} clearcoat={1} emissive={CYAN} emissiveIntensity={0.16} />
      </mesh>
      {/* chest keyhole */}
      <mesh geometry={keyholeGeo} position={[0, -1.3, 0.56]} rotation={[0, 0, 0]}>
        <meshBasicMaterial color={CYAN} toneMapped={false} />
      </mesh>

      {/* head: shield hood + visor + face */}
      <group ref={head} position={[0, 0.35, 0]}>
        <mesh geometry={headGeo} position={[0, 0, -0.3]}>
          <meshPhysicalMaterial color="#f3e6d8" roughness={0.32} clearcoat={0.9} clearcoatRoughness={0.2} sheen={0.6} sheenColor="#ffffff" />
        </mesh>
        <mesh geometry={visorGeo} position={[0, 0, 0.3]}>
          <meshPhysicalMaterial color="#0a1220" roughness={0.08} metalness={0.4} clearcoat={1} clearcoatRoughness={0.03} />
        </mesh>
        <group ref={eyes} position={[0, 0.12, 0.37]}>
          <mesh position={[-0.27, 0, 0]} scale={[0.15, 0.2, 0.06]}>
            <sphereGeometry args={[1, 32, 24]} />
            <meshBasicMaterial color={CYAN} toneMapped={false} />
          </mesh>
          <mesh position={[0.27, 0, 0]} scale={[0.15, 0.2, 0.06]}>
            <sphereGeometry args={[1, 32, 24]} />
            <meshBasicMaterial color={CYAN} toneMapped={false} />
          </mesh>
        </group>
        <mesh position={[0, -0.18, 0.37]} rotation={[0, 0, Math.PI]}>
          <torusGeometry args={[0.12, 0.018, 12, 32, Math.PI]} />
          <meshBasicMaterial color={CYAN} toneMapped={false} />
        </mesh>
      </group>
    </group>
  )
}

export function Passbot3D() {
  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ position: [0, 0.15, 9.4], fov: 32 }}
      gl={{ alpha: true, antialias: true }}
      style={{ background: 'transparent' }}
    >
      <hemisphereLight args={['#fff7ee', '#8fd3f5', 0.85]} />
      <directionalLight position={[3, 4, 5]} intensity={2.2} />
      <directionalLight position={[-4, 1, 3]} intensity={0.9} color="#a5f3fc" />
      <pointLight position={[0, -1.3, 1.6]} intensity={6} distance={4} color={CYAN} />
      <Bot />
      <Sparkles />
      <EffectComposer>
        <Bloom intensity={0.9} luminanceThreshold={0.85} luminanceSmoothing={0.2} mipmapBlur />
      </EffectComposer>
    </Canvas>
  )
}
