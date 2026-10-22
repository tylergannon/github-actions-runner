import AppKit

// A small native vector drawing, rasterized at the sizes required by iconutil.
let output = CommandLine.arguments[1]
try FileManager.default.createDirectory(atPath: output, withIntermediateDirectories: true)
for size in [16, 32, 128, 256, 512] {
    for scale in [1, 2] {
        let pixels = size * scale
        let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: pixels,
            pixelsHigh: pixels, bitsPerSample: 8, samplesPerPixel: 4,
            hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
            bytesPerRow: 0, bitsPerPixel: 0)!
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
        let context = NSGraphicsContext.current!.cgContext
        context.scaleBy(x: CGFloat(pixels) / 1024, y: CGFloat(pixels) / 1024)
        NSColor(calibratedRed: 0.12, green: 0.30, blue: 0.66, alpha: 1).setFill()
        NSBezierPath(roundedRect: NSRect(x: 48, y: 48, width: 928, height: 928),
            xRadius: 208, yRadius: 208).fill()
        NSColor.white.setStroke()
        let connections = NSBezierPath()
        connections.lineWidth = 48
        connections.move(to: NSPoint(x: 280, y: 700))
        connections.line(to: NSPoint(x: 280, y: 330))
        connections.line(to: NSPoint(x: 610, y: 330))
        connections.stroke()
        NSColor.white.setFill()
        for y in [330, 700] {
            NSBezierPath(ovalIn: NSRect(x: 200, y: y - 80, width: 160, height: 160)).fill()
        }
        let play = NSBezierPath()
        play.move(to: NSPoint(x: 580, y: 190))
        play.line(to: NSPoint(x: 810, y: 330))
        play.line(to: NSPoint(x: 580, y: 470))
        play.close()
        play.fill()
        NSGraphicsContext.restoreGraphicsState()
        let suffix = scale == 2 ? "@2x" : ""
        let path = "\(output)/icon_\(size)x\(size)\(suffix).png"
        try bitmap.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: path))
    }
}
