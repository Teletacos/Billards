from math import trunc
from random import random, randrange

import pygame, time, math
from pygame import Vector2, Rect
from pygame.math import clamp

pygame.init()
pygame.display.set_caption("Billards for idiots")
display_size = pygame.display.Info()

screen_size = (display_size.current_w, display_size.current_h)
center = [int(screen_size[0]/2), int(screen_size[1]/2)]

screen = pygame.display.set_mode((screen_size[0], screen_size[1]), pygame.RESIZABLE)
canvas = pygame.Surface((display_size.current_w, display_size.current_h))

x_bounds = [100, display_size.current_w - 100]
y_bounds = [100, display_size.current_h - 100]

holes = (
  (x_bounds[0], 100),
  (center[0], 100),
  (x_bounds[1], 100),
  (x_bounds[0], display_size.current_h - 100),
  (center[0], display_size.current_h - 100),
  (x_bounds[1], display_size.current_h - 100)
)

background = pygame.image.load("graphics/background.png").convert()
background = pygame.transform.scale(background, screen_size)

stick_image = pygame.image.load("graphics/stick.png").convert_alpha()
stick_image = pygame.transform.scale(stick_image, [700, 20])

stick_shadow_image = pygame.image.load("graphics/stick_shadow.png").convert_alpha()
stick_shadow_image = pygame.transform.scale(stick_shadow_image, [700, 20])

ball_shadow = pygame.image.load("graphics/ball_shadow.png").convert_alpha()

ball_hit_sound = pygame.mixer.Sound("sounds/ball_hit.mp3")
stick_hit_sound = pygame.mixer.Sound("sounds/stick_hit.mp3")
hole_sound = pygame.mixer.Sound("sounds/hole.mp3")

font = pygame.font.SysFont("Arial", 30)

shadow_offset = Vector2(8, 6)

def lerp(a, b, t):
  return a + (b - a) * t

def sign(a):
  if a >= 0:
    return 1
  elif a < 0:
    return -1

  def lerp(a, b, t):
    return (1 - t) * a + t * b

def generate_pyramid(position, radius, spacing, columns, match_instance):
  total_spacing = radius * 2 + spacing

  i = 1

  for column in range(columns):
    x = position.x + column * total_spacing

    y_count = columns - column
    y_start = position.y - (y_count - 1) * total_spacing / 2

    for row in range(y_count):
      y = y_start + row * total_spacing
      color = (randrange(0, 255), randrange(0, 255), randrange(0, 255))
      ball = Ball(Vector2(x, y), radius, Vector2(0, 0), i, match_instance)
      i += 1

def get_random_ball_in_hole(type):
  available = []
  for ball in balls:
    if not ball.in_hole and ball.type == type:
      available.append(ball)

  return available[randrange(0, len(available))]

def is_balls_still():
  for ball in balls:
    if ball.velocity.magnitude() > 0:
      return False
  return True

class Ball:
  def __init__(self, position, radius, velocity, index, match_instance):
    self.type = "White"
    if 0 < index < 8:
      self.type = "Full"
    elif index == 8:
      self.type = "Eight"
    elif index > 8:
      self.type = "Stripes"

    # Physics config
    self.friction = 20
    self.wall_bounce_ratio = 0.6
    self.ball_bounce_ratio = 0.95
    self.rotation_friction = 50
    self.spin_influence = 0.01
    self.spin_margin = 0.96 # 1 - 100% of shots - 0.96

    self.rotation_velocity = 0
    self.rotation = 0
    self.velocity = velocity
    self.position = position
    self.base_radius = radius
    self.radius = radius
    self.collision_margin = 0.1

    self.holding = False
    self.hold_power = 0
    self.max_hold_power = 200
    self.hold_direction = Vector2(0, 0)

    self.hole_t = 0
    self.hole_start = None
    self.hole_position = None
    self.in_hole = False
    self.grabbed = False

    self.base_image = pygame.image.load(f"graphics/balls/{index}.png").convert_alpha()
    self.image = self.base_image

    self.match = match_instance

    balls.append(self)

  def check_bound_collision(self):
    if self.position.x - self.radius < x_bounds[0]:
      self.position.x = x_bounds[0] + self.radius
      self.velocity.x = -self.velocity.x * self.wall_bounce_ratio
    elif self.position.x + self.radius > x_bounds[1]:
      self.position.x = x_bounds[1] - self.radius
      self.velocity.x = -self.velocity.x * self.wall_bounce_ratio
    if self.position.y - self.radius < y_bounds[0]:
      self.position.y = y_bounds[0] + self.radius
      self.velocity.y = -self.velocity.y * self.wall_bounce_ratio
    elif self.position.y + self.radius > y_bounds[1]:
      self.position.y = y_bounds[1] - self.radius
      self.velocity.y = -self.velocity.y * self.wall_bounce_ratio

  def calculate_spin(self, hit_direction, velocity_direction):
    print(velocity_direction.dot(-hit_direction))
    if velocity_direction.dot(-hit_direction) > self.spin_margin: return 0
    print("Success")
    if hit_direction.x < 0 and hit_direction.y > 0:  # Lower left quadrant
      print("Lower left")
      if velocity_direction.x < 0 and velocity_direction.y < 0:
        return -1
      else:
        return 1

    if hit_direction.x > 0 and hit_direction.y < -0:  # Upper right quadrant
      print("Upper right")
      if velocity_direction.x < 0 and velocity_direction.y < 0:
        return 1
      else:
        return -1

    if hit_direction.x > 0 and hit_direction.y > 0:  # Lower right quadrant
      print("Lower right")
      if velocity_direction.x < 0 and velocity_direction.y > 0:
        return -1
      else:
        return 1

    if hit_direction.x < -0 and hit_direction.y < -0:  # Upper left quadrant
      print("Upper left")
      if velocity_direction.x > 0 or velocity_direction.y < 0:
        return -1
      else:
        return 1

    return 0

  def check_ball_collision(self, ball):
    if ball.in_hole or self.in_hole or self.grabbed or ball.grabbed: return
    direction = (ball.position - self.position).normalize()
    distance = (ball.position - self.position).magnitude()
    total_radius = ball.radius + self.radius

    if distance - total_radius <= 0:
      if ball.velocity.magnitude() > self.velocity.magnitude():
        hit_direction = direction
        velocity_direction = ball.velocity.normalize()
        self.rotation_velocity = self.calculate_spin(hit_direction, velocity_direction) * ball.velocity.magnitude() * 10
      elif self.velocity.magnitude() > ball.velocity.magnitude():
        hit_direction = direction * -1
        velocity_direction = self.velocity.normalize()
        ball.rotation_velocity = self.calculate_spin(hit_direction, velocity_direction) * self.velocity.magnitude() * 10

        pygame.draw.circle(screen, (100, 100, 100) ,(self.position + hit_direction), 25)

      normal = direction
      tangent = Vector2(-direction.y, direction.x) # Normal turned 90 degrees
      v1_normal = self.velocity.dot(normal) # Self velocity along normal
      v1_tangent = self.velocity.dot(tangent) # Self velocity along tangent
      v2_normal = ball.velocity.dot(normal) # Other velocity along normal
      v2_tangent = ball.velocity.dot(tangent)  # Other velocity along normal

      v1 = v2_normal * normal + v1_tangent * tangent
      v2 = v1_normal * normal + v2_tangent * tangent

      self.velocity = v1 * self.ball_bounce_ratio
      ball.velocity = v2 * ball.ball_bounce_ratio

      self.position += direction * (abs(distance - total_radius) + self.collision_margin) * -1
      if abs(v1_normal) + abs(v2_normal) > 5:
        ball_hit_sound.play()

  def check_hole_collisions(self):
    for hole_pos in holes:
      distance = (Vector2(hole_pos) - self.position).magnitude()
      total_distance = distance - self.radius
      if not self.hole_position and total_distance < 20:
        hole_sound.play()
        self.hole_position = hole_pos
        self.hole_start = self.position
        self.hole_t = 0

  def check_stick_collision(self, stick):
    if not stick.is_moving: return
    hit_direction = (stick.position - self.position).normalize()
    distance = (stick.position - self.position).magnitude()
    total_radius = stick.radius + self.radius

    if distance - total_radius <= 0:
      normal = hit_direction
      stick_normal = (stick.direction * stick.speed).dot(normal)
      self.rotation_velocity = self.calculate_spin(hit_direction, stick.direction) * stick.speed / 2
      self.velocity = normal * stick_normal / 10
      self.match.stick_hit()
      stick_hit_sound.play()
      stick.reset()

  def move(self, dt):
    if self.grabbed: return

    if self.hole_position:
        if self.hole_t >= 1:
          self.in_hole = True
          self.hole_position = None
          self.velocity = Vector2(0, 0)
          self.match.ball_holed(self)
        else:
          self.position = Vector2.lerp(self.hole_start, self.hole_position, self.hole_t)
          self.radius = lerp(self.base_radius, self.base_radius/1.5, self.hole_t)
          self.hole_t += dt * 4
    elif not self.in_hole:
      self.check_hole_collisions()
      self.check_bound_collision()
      speed = self.velocity.magnitude()
      if speed > 0.01: # Deadzone to avoid jittering
        velocity_direction = self.velocity.normalize()
        friction_velocity = velocity_direction * -self.friction
        if (self.velocity + friction_velocity * dt).magnitude() > speed:
          self.velocity = Vector2(0, 0)
        else:
          self.velocity += friction_velocity * dt

        spin_velocity = Vector2(velocity_direction.y, -velocity_direction.x) * self.rotation_velocity * self.spin_influence
        self.velocity += spin_velocity * dt
        self.position += self.velocity * dt * 10
      else:
        self.velocity = Vector2(0, 0)

      rotation_friction = sign(self.rotation_velocity) * self.rotation_friction
      rotation_friction = clamp(rotation_friction, -abs(self.rotation_velocity), abs(self.rotation_velocity))
      self.rotation_velocity -= rotation_friction * dt * 10
      self.rotation += self.rotation_velocity * dt

  def draw(self, surface):
    if not self.in_hole:
      # Shadow
      #pygame.draw.circle(surface, (24, 59, 22), self.position + Vector2(6, 6), self.radius)
      shadow_image = pygame.transform.scale(ball_shadow, [self.radius * 2, self.radius * 2])
      shadow_image = pygame.transform.rotate(shadow_image, self.rotation)
      shadow_rect = shadow_image.get_rect(center=self.position + shadow_offset)
      surface.blit(shadow_image, shadow_rect)

      # Ball
      self.image = pygame.transform.scale(self.base_image, [self.radius * 2, self.radius * 2])
      self.image = pygame.transform.rotate(self.image, self.rotation)
      image_rect = self.image.get_rect(center = self.position)
      surface.blit(self.image, image_rect)

class Stick:
  def __init__(self, image, shadow_image, match_instance):
    self.position = None
    self.start_position = None
    self.end_position = None
    self.speed = 0
    self.acceleration = 7000
    self.direction = 0
    self.angle = 0
    self.radius = 25
    self.is_moving = False
    self.hit_time = 0
    self.length = image.get_rect().size[0]
    self.image = image
    self.shadow_image = shadow_image
    self.match = match_instance

  def detect_mouse_press(self):
    if not self.is_moving:
      mouse_pos = pygame.mouse.get_pos()
      if pygame.mouse.get_pressed()[0] and not self.match.round_ongoing:
        if not self.end_position:
          self.end_position = Vector2(mouse_pos[0], mouse_pos[1])
      else:
        if self.end_position:
          self.start_position = Vector2(mouse_pos[0], mouse_pos[1])
          self.start_move()

  def start_move(self):
    if (self.end_position - self.start_position).magnitude() > 2:
      self.position = self.start_position
      self.direction = (self.end_position - self.start_position).normalize()
      self.angle = math.pi * 2 - math.atan2(self.direction.y, self.direction.x)
      self.is_moving = True

  def move(self):
    if self.is_moving:
        magnitude = ((self.end_position + self.direction * 140) - self.position).magnitude() # Go a little past endpos
        if magnitude > 40:
          self.speed += self.acceleration * dt
          self.position += self.speed * self.direction * dt
        else:
          self.reset()

  def reset(self):
    self.start_position = None
    self.end_position = None
    self.is_moving = False
    self.speed = 0
    self.hit_time = time.time()

  def get_bound_direction(self, position, direction):
    if position.x - self.radius < x_bounds[0]:
      position.x = x_bounds[0] + self.radius
      direction.x = -direction.x
    elif position.x + self.radius > x_bounds[1]:
      position.x = x_bounds[1] - self.radius
      direction.x = -direction.x
    if position.y - self.radius < y_bounds[0]:
      position.y = y_bounds[0] + self.radius
      direction.y = -direction.y
    elif position.y + self.radius > y_bounds[1]:
      position.y = y_bounds[1] - self.radius
      direction.y = -direction.y
    return direction

  def draw(self):
    if self.is_moving or time.time() - self.hit_time < 2:
      new_image = pygame.transform.rotate(self.image, math.degrees(self.angle))
      new_shadow_image = pygame.transform.rotate(self.shadow_image, math.degrees(self.angle))

      image_rect = new_image.get_rect()
      image_rect.center = self.position - self.direction * self.length / 2

      shadow_rect = Rect(image_rect)
      shadow_rect.center = shadow_rect.center + shadow_offset * 1.5

      canvas.blit(new_shadow_image, shadow_rect)
      canvas.blit(new_image, image_rect)
    elif self.end_position:
      # Draw indicator

      mouse_pos = pygame.mouse.get_pos()
      offset = (Vector2(mouse_pos[0], mouse_pos[1]) - self.end_position)
      distance = offset.magnitude()
      if distance > 0:
        step_length = 15
        steps = int(distance/step_length) * 3

        last_direction = (self.end_position - mouse_pos).normalize()
        last_position = self.end_position
        for i in range(steps):
          new_direction = self.get_bound_direction(last_position, last_direction)
          new_pos = last_position + new_direction * step_length
          last_position = new_pos
          last_direction = new_direction
          pygame.draw.circle(canvas, (255, 255, 255), new_pos, 4)

class Match:
  def __init__(self):

    self.grabbed_ball = None
    self.mouse_down = False

    self.round_ongoing = False
    self.current_type = ""
    self.next_type = ""
    self.full_left = 7
    self.stripes_left = 7

  def change_score(self, type, amount):
    if type == "Full":
      self.full_left += amount
    elif type == "Stripes":
      self.stripes_left += amount

  def ball_holed(self, ball):
    if ball.type == "White":
        ball.position = Vector2(1000, center[1]) # Reset white ball pos
        ball.radius = ball.base_radius
        self.grabbed_ball = ball
        self.grabbed_ball.in_hole = False
        self.grabbed_ball.grabbed = True

        self.change_score(self.current_type, 1)
    elif self.current_type == "":
      # Set color, continue round
      self.current_type = ball.type
      self.change_score(self.current_type, -1)
      self.next_type = self.current_type
    elif self.current_type == ball.type:
      self.change_score(self.current_type, -1)
      self.next_type = self.current_type
    elif self.current_type != ball.type:
      self.current_type = ball.type
      self.change_score(self.current_type, -1)

  def stick_hit(self):
    self.round_ongoing = True
    if self.current_type == "Full":
      self.next_type = "Stripes"
    elif self.current_type == "Stripes":
      self.next_type = "Full"

  def update(self):
    if is_balls_still() and not self.grabbed_ball:
      self.round_ongoing = False
      self.current_type = self.next_type

    if self.grabbed_ball:
      mouse_pos = pygame.mouse.get_pos()
      if pygame.mouse.get_pressed()[0]:
        self.mouse_down = True
      elif self.mouse_down:
        self.mouse_down = False
        self.grabbed_ball.grabbed = False
        self.grabbed_ball = None
      else:
        self.grabbed_ball.position = Vector2(mouse_pos[0], mouse_pos[1])

match = Match()
balls = []
generate_pyramid(Vector2(300, center[1]), 25, 5, 5, match)
white_ball = Ball(Vector2(1000, center[1]), 25, Vector2(0, 0), 0, match)

player_stick = Stick(stick_image, stick_shadow_image, match)

last_time = time.time()
last_mouse_pos = Vector2(0, 0)

while True:
  dt = time.time() - last_time
  last_time = time.time()

  # The game has a winner
  for event in pygame.event.get():
    if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
      exit()

  # CALCULATION
  match.update()

  player_stick.detect_mouse_press()
  player_stick.move()

  white_ball.check_stick_collision(player_stick)
  for ball in balls:
    ball.move(dt)

  for ball in balls:
    for other_ball in balls:
      if other_ball != ball:
        ball.check_ball_collision(other_ball)

  # GRAPHICS
  background_rect = background.get_rect()
  background_rect.center = center
  canvas.blit(background, background_rect)

  for hole in holes:
    pygame.draw.circle(canvas, (0, 0, 0), (hole[0], hole[1]), 10)

  for ball in balls:
    ball.draw(canvas)

  player_stick.draw()

  full_score_surface = font.render(str(match.full_left), True, (255, 255, 255))  # White text
  canvas.blit(full_score_surface, (0, 0))

  stripes_score_surface = font.render(str(match.stripes_left), True, (255, 255, 255))  # White text
  canvas.blit(stripes_score_surface, (50, 0))

  type_surface = font.render(str(match.current_type), True, (255, 255, 255))  # White text
  canvas.blit(type_surface, (100, 0))

  screen.blit(pygame.transform.scale(canvas, (screen.get_width(), screen.get_height())), (0, 0))
  pygame.display.flip()