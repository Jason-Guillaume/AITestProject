declare module 'dddocr' {
  // Minimal type declaration for the npm package used in Playwright tests.
  // The actual API may provide more methods; we only need `classification`.
  interface DdddOcr {
    classification(image: Buffer | Uint8Array): Promise<string>
  }
  const DdddOcr: new () => DdddOcr
  export default DdddOcr
}
