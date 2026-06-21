from manim import *

class SteamEngineAnimation(Scene):
    def construct(self):
        # --- Configuration ---
        crank_pin_radius = 1.0  # Manim units, defines the "throw" of the crankshaft
        connecting_rod_length = 4.0
        piston_width = 1.0
        piston_height = 1.8
        animation_speed = 0.5 # radians per second, controls speed of rotation

        # --- Components ---
        # Crankshaft and Wheel
        crankshaft_center = LEFT * 2
        # Scale SVGs. The scale factor is chosen for visual appeal;
        # the crank_pin_radius is used for geometric calculations.
        crankshaft_svg = SVGMobject("crankshaft.svg").scale(1.5).move_to(crankshaft_center)
        wheel_svg = SVGMobject("wheel.svg").scale(1.5).move_to(crankshaft_center + RIGHT * 3.5)

        # Cylinder and Piston
        cylinder_center = crankshaft_center + LEFT * 4.5
        cylinder = Rectangle(width=3, height=2, color=GREY_C, fill_opacity=0.3).move_to(cylinder_center)
        piston_y_level = cylinder_center.get_y() # Piston moves horizontally at this y-level
        piston = Rectangle(width=piston_width, height=piston_height, color=BLUE_B, fill_opacity=0.8)

        # Connecting Rod and Pins (dots for visual reference)
        connecting_rod = Line(ORIGIN, ORIGIN, color=GRAY_A, stroke_width=8)
        crank_pin_dot = Dot(color=YELLOW_A, radius=0.08)
        piston_pin_dot = Dot(color=YELLOW_A, radius=0.08)

        # Steam System
        # Ports are located relative to the cylinder
        steam_in_port_pos = cylinder.get_top() + LEFT * 0.5
        steam_out_port_pos = cylinder.get_bottom() + LEFT * 0.5
        
        # Boiler
        boiler_pos = DOWN * 3 + RIGHT * 5
        boiler = Rectangle(width=2.5, height=1.5, color=ORANGE, fill_opacity=0.8).move_to(boiler_pos)
        boiler_text = Text("Boiler").next_to(boiler, UP, buff=0.2).scale(0.7)

        # Labels for steam ports
        steam_in_label = Text("Steam In", font_size=24, color=BLUE_A).next_to(steam_in_port_pos, UP, buff=0.2)
        steam_out_label = Text("Steam Out", font_size=24, color=RED_A).next_to(steam_out_port_pos, DOWN, buff=0.2)
        
        # Steam paths as Arrows to show direction of flow
        steam_to_cylinder_path = Arrow(start=steam_in_port_pos + LEFT*1.5, end=steam_in_port_pos, color=BLUE_A, stroke_width=5, buff=0)
        steam_from_cylinder_path = Arrow(start=steam_out_port_pos, end=steam_out_port_pos + LEFT*1.5, color=RED_A, stroke_width=5, buff=0)
        
        # Curved path for steam return using VMobject for a custom path
        steam_return_path = VMobject(color=PURPLE_A, stroke_width=5)
        # Define points to create a curved path from exhaust to boiler
        start_point_return = steam_out_port_pos + LEFT * 1.5
        control_point_return = boiler.get_center() + UP * 1.5 + LEFT * 1.5
        end_point_return = boiler.get_top() + RIGHT * 0.5
        steam_return_path.set_points_as_corners([start_point_return, control_point_return, end_point_return])


        # --- Animation Logic ---
        angle_tracker = ValueTracker(0) # Tracks the angle of rotation for the crankshaft

        # Updater function for the entire mechanism
        def update_piston_mechanism(mob):
            theta = angle_tracker.get_value()

            # Calculate crank pin position relative to crankshaft_center
            crank_pin_x = crankshaft_center[0] + crank_pin_radius * np.cos(theta)
            crank_pin_y = crankshaft_center[1] + crank_pin_radius * np.sin(theta)
            crank_pin_pos = np.array([crank_pin_x, crank_pin_y, 0])

            # Calculate piston pin x position (slides horizontally at piston_y_level)
            # This uses the law of cosines implicitly: L^2 = (dx)^2 + (dy)^2
            # dx = sqrt(L^2 - dy^2)
            delta_y = crank_pin_y - piston_y_level
            dx_squared = connecting_rod_length**2 - delta_y**2
            
            # Prevent sqrt of negative in case of floating point inaccuracies or extreme values
            if dx_squared < 0:
                dx_squared = 0

            # The piston pin is typically to the left of the crank pin for the power stroke
            piston_pin_x = crank_pin_x - np.sqrt(dx_squared)
            piston_pin_pos = np.array([piston_pin_x, piston_y_level, 0])

            # Update piston position (center the piston horizontally around its pin)
            piston.move_to(piston_pin_pos + LEFT * piston_width/2)

            # Update connecting rod by setting its start and end points
            connecting_rod.put_start_and_end_on(piston_pin_pos, crank_pin_pos)

            # Update dots (representing the pins for clarity)
            piston_pin_dot.move_to(piston_pin_pos)
            crank_pin_dot.move_to(crank_pin_pos)

            # Update crankshaft rotation (assumes SVG arm points right at 0 rotation)
            crankshaft_svg.set_rotation(theta)

            # Update wheel rotation (assume 1:1 ratio with crankshaft for simplicity)
            wheel_svg.set_rotation(theta)

        # Group all dynamic parts and apply the updater
        mechanism_elements = VGroup(
            crankshaft_svg, wheel_svg, piston, connecting_rod,
            crank_pin_dot, piston_pin_dot
        )
        mechanism_elements.add_updater(update_piston_mechanism)
        
        # Make the angle tracker update over time, driving the animation
        angle_tracker.add_updater(lambda m, dt: m.increment_value(dt * animation_speed))


        # --- Scene Animations ---
        # 1. Introduce the main mechanical components
        self.play(
            FadeIn(crankshaft_svg, shift=LEFT),
            FadeIn(wheel_svg, shift=RIGHT),
            FadeIn(cylinder, shift=LEFT),
            FadeIn(piston, shift=LEFT),
            FadeIn(connecting_rod, shift=LEFT),
            FadeIn(crank_pin_dot, piston_pin_dot),
            run_time=2
        )
        self.wait(0.5)

        # 2. Add angle_tracker and the mechanism group to the scene to start continuous motion
        self.add(angle_tracker, mechanism_elements)
        
        # Let the mechanism run for a short period (e.g., one full rotation) to establish its motion
        self.play(
            angle_tracker.animate.set_value(TAU * 1), # One full rotation (TAU = 2*PI)
            run_time=TAU / animation_speed, # Calculate run_time based on desired speed
            rate_func=linear
        )
        self.wait(1)

        # 3. Introduce Steam System elements while the mechanism continues running
        self.play(
            FadeIn(boiler, boiler_text, shift=UP),
            FadeIn(steam_in_label, steam_out_label),
            run_time=1.5
        )
        self.wait(0.5)

        # 4. Illustrate Steam Flow in loops while the mechanism continues its motion
        num_steam_cycles_to_show = 3 # Number of steam cycles to demonstrate
        for i in range(num_steam_cycles_to_show):
            # Steam In (first half of the cycle, piston moves right)
            self.play(
                ShowPassingFlash(steam_to_cylinder_path, run_time=0.8, time_width=0.4, color=BLUE_A),
                angle_tracker.animate.set_value(angle_tracker.get_value() + PI), # Half rotation (PI radians)
                run_time=PI / animation_speed, # Match run_time to half a cycle
                rate_func=linear
            )
            self.wait(0.2) # Small pause to differentiate intake/exhaust phases

            # Steam Out & Return (second half of the cycle, piston moves left)
            self.play(
                ShowPassingFlash(steam_from_cylinder_path, run_time=0.8, time_width=0.4, color=RED_A),
                ShowPassingFlash(steam_return_path, run_time=1.2, time_width=0.4, color=PURPLE_A),
                angle_tracker.animate.set_value(angle_tracker.get_value() + PI), # Next half rotation
                run_time=PI / animation_speed, # Match run_time to half a cycle
                rate_func=linear
            )
            self.wait(0.5) # Pause at end of full cycle before repeating (if in a loop)

        self.wait(1) # Final pause

        # 5. Final Fade Out of all objects on screen
        self.play(
            FadeOut(self.mobjects), # This will fade out everything currently added to the scene
            run_time=1.5
        )
        self.wait(1) # Final wait before scene ends