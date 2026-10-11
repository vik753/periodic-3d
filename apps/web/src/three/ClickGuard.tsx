/**
 * An invisible sphere around a model. A click into the model's gaps (between atoms, on
 * bonds or orbits) hits the guard, so it does not count as a click on empty space, which
 * leads back to the table (Scene, onPointerMissed). The guard does not stop the event:
 * beads and tiles behind it still get their clicks. Raycasting ignores `visible`, so the
 * sphere is hit-tested but never drawn.
 */
export function ClickGuard({ radius }: { radius: number }) {
  return (
    <mesh visible={false} scale={radius} onClick={keepScene}>
      <sphereGeometry args={[1, 16, 12]} />
    </mesh>
  );
}

function keepScene(): void {
  // Intentionally empty: being hit is the guard's whole job.
}
