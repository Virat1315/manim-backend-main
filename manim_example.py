# from manim import *

# class RainProblem(Scene):
#     def construct(self):
#         cloud1 = SVGMobject("/home/aryan/IMP/mentrax_AI/cloud-rain-svgrepo-com.svg").scale(0.5).to_corner(UL).set_opacity(0.3)
#         cloud2 = SVGMobject("/home/aryan/IMP/mentrax_AI/cloud-rain-svgrepo-com.svg").scale(0.6).to_corner(UR).shift(DOWN * 0.5).set_opacity(0.3)
#         cloud3 = SVGMobject("/home/aryan/IMP/mentrax_AI/cloud-rain-svgrepo-com.svg").scale(0.4).move_to(LEFT * 3 + UP * 2).set_opacity(0.2)

#         clouds = VGroup(cloud1, cloud2, cloud3)
#         self.add(clouds)  # Add before anything else to keep them in the background
#         # Scene 1: Problem Introduction
#         intro_text = Tex(r"""
#         A man running on a horizontal road at 8 km/h 
#         finds the rain falling vertically. He increases 
#         his speed to 12 km/h and finds that the drops 
#         make an angle 30$^\circ$ with the vertical.
#         """).scale(0.7).to_edge(UP)
#         self.play(Write(intro_text))
#         self.wait(2)
#         self.play(FadeOut(intro_text))

#         # Scene 2: Real-life animation: Man running, rain falling vertically
#         road = Line(LEFT * 5, RIGHT * 5).shift(DOWN * 2)
#         man = SVGMobject("/home/aryan/IMP/mentrax_AI/running-svgrepo-com.svg").scale(0.5).shift(LEFT * 3 + DOWN * 1.5)
#         rain_drops = VGroup(*[
#             Line(UP * 0.2, DOWN * 0.2).shift(RIGHT * x + UP * 2)
#             for x in range(-5, 6)
#         ])

#         self.play(Create(road), FadeIn(man))
#         self.play(*[Create(drop) for drop in rain_drops])
#         self.wait(0.5)

#         self.play(
#             man.animate.shift(RIGHT * 6),
#             *[drop.animate.shift(DOWN * 4) for drop in rain_drops],
#             run_time=3
#         )
#         self.wait(1)
#         self.play(FadeOut(man, road, *rain_drops))

#         # Scene 3: Observation with angled rain
#         man_fast = SVGMobject("/home/aryan/IMP/mentrax AI/running-svgrepo-com.svg").scale(0.5).shift(LEFT * 3 + DOWN * 1.5)
#         rain_slant = VGroup(*[
#             Line(UP * 0.3, DOWN * 0.3).rotate(-PI/6).shift(RIGHT * x + UP * 2)
#             for x in range(-5, 6)
#         ])

#         self.play(FadeIn(man_fast))
#         self.play(*[Create(drop) for drop in rain_slant])
#         self.wait(0.5)

#         self.play(
#             man_fast.animate.shift(RIGHT * 6),
#             *[drop.animate.shift(DOWN * 4 + RIGHT * 2) for drop in rain_slant],
#             run_time=3
#         )
#         self.wait(1)
#         self.play(FadeOut(man_fast, *rain_slant))

#         # Scene 4: Vector Explanation
#         self.clear()
#         vec_eq = MathTex(
#             r"\vec{v}_{\text{rain, road}} = \vec{v}_{\text{rain, man}} + \vec{v}_{\text{man, road}}"
#         )
#         self.play(Write(vec_eq))
#         self.wait(2)
#         self.play(FadeOut(vec_eq))

#         # Scene 5: Vector Diagram
#         man_vec = Arrow(LEFT * 2, RIGHT * 2, color=BLUE).shift(DOWN)
#         rain_vec = Arrow(UP * 2, DOWN * 2, color=YELLOW).next_to(man_vec.get_start(), UP)
#         result_vec = Arrow(rain_vec.get_start(), man_vec.get_end(), color=GREEN)

#         label_man = MathTex(r"8 \text{ km/h}").next_to(man_vec, DOWN)
#         label_rain_man = MathTex(r"\vec{v}_{\text{rain, man}}").next_to(rain_vec, LEFT)
#         label_rain_road = MathTex(r"\vec{v}_{\text{rain, road}}").next_to(result_vec, UP)

#         self.play(Create(man_vec), Write(label_man))
#         self.play(Create(rain_vec), Write(label_rain_man))
#         self.play(Create(result_vec), Write(label_rain_road))
#         self.wait(2)
#         self.play(FadeOut(man_vec, rain_vec, result_vec, label_man, label_rain_man, label_rain_road))

#         # Scene 6: Observation Angle
#         angle = Angle(Line(ORIGIN, ORIGIN + DOWN), Line(ORIGIN, ORIGIN + UL), radius=0.6)
#         angle_label = MathTex(r"30^\circ").next_to(angle, RIGHT)
#         self.play(Create(angle), Write(angle_label))
#         self.wait(2)
#         self.play(FadeOut(angle, angle_label))

#         # Scene 7: Equation solving
#         eq1 = MathTex(r"v_{\text{rain, road}} \sin \alpha = 8").to_edge(UP)
#         eq2 = MathTex(r"v_{\text{rain, road}} \sin(30^\circ + \alpha) = 12 \cos 30^\circ").next_to(eq1, DOWN, buff=1)
#         self.play(Write(eq1), Write(eq2))
#         self.wait(2)

#         simp1 = MathTex(r"\frac{\sin(30^\circ + \alpha)}{\sin\alpha} = \frac{12 \sqrt{3}}{8 \times 2}").next_to(eq2, DOWN)
#         simp2 = MathTex(r"\cot \alpha = \frac{\sqrt{3}}{2}").next_to(simp1, DOWN)
#         simp3 = MathTex(r"\alpha = \cot^{-1} \left( \frac{\sqrt{3}}{2} \right)").next_to(simp2, DOWN)

#         self.play(Write(simp1))
#         self.wait(1)
#         self.play(Write(simp2))
#         self.wait(1)
#         self.play(Write(simp3))
#         self.wait(2)

#         # Final Answer
#         final = MathTex(r"v_{\text{rain, road}} = \frac{8}{\sin \alpha} = 4\sqrt{7} \text{ km/h}").scale(1.2).set_color(YELLOW)
#         self.play(Write(final))
#         self.wait(3)
import manim
import inspect
import json

# Dictionary to store all class information
classes_dict = {}
functions_list = []

# Get all classes in manim module
for name, obj in inspect.getmembers(manim):
    if inspect.isclass(obj) and obj.__module__.startswith('manim'):
        class_info = {"methods": [], "attributes": []}
        
        # Get methods
        methods = inspect.getmembers(obj, predicate=inspect.isfunction)
        for method_name, method in methods:
            if method_name.startswith('_'):
                continue  # Skip private methods
                
            try:
                # Get signature
                signature = inspect.signature(method)
                params = []
                for param_name, param in signature.parameters.items():
                    if param.default is inspect.Parameter.empty:
                        params.append(param_name)
                    else:
                        params.append(f"{param_name}={param.default}")
                
                param_str = ", ".join(params)
                class_info["methods"].append(f"{method_name}({param_str})")
            except (ValueError, TypeError):
                class_info["methods"].append(f"{method_name}(...)")

        # Get attributes
        for attr_name, attr_value in vars(obj).items():
            if not attr_name.startswith('_'):  # Skip private attributes
                class_info["attributes"].append(attr_name)
        
        # Add to main dictionary
        classes_dict[obj.__name__] = class_info
    
    # Collect non-class functions
    elif inspect.isfunction(obj) and obj.__module__.startswith('manim'):
        try:
            signature = inspect.signature(obj)
            params = []
            for param_name, param in signature.parameters.items():
                if param.default is inspect.Parameter.empty:
                    params.append(param_name)
                else:
                    params.append(f"{param_name}={param.default}")
            
            param_str = ", ".join(params)
            functions_list.append(f"{name}({param_str})")
        except (ValueError, TypeError):
            functions_list.append(f"{name}(...)")

# Add functions to the output dictionary (optional)
classes_dict["_functions"] = {"methods": functions_list, "attributes": []}

# Write to JSON file
with open("manim_documentation.json", "w") as f:
    json.dump(classes_dict, f, indent=2)

print("Documentation written to manim_documentation.json")
